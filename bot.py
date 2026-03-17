"""
Discord bot for Personal Knowledge Base.
Drop URLs in the configured channel to auto-ingest content.
"""
import asyncio
import discord
from discord.ext import commands
import re
import io
from typing import Optional

from kb.database import init_db, get_stats
from kb.search import hybrid_search, search_by_entity
from kb.ingest import detect_source_type, process_and_store

# Try to import LLM RAG, but don't fail if it's not available
try:
    from kb.llm_rag import rag_query, rewrite_query_for_search
    LLM_RAG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: LLM RAG not available: {e}")
    LLM_RAG_AVAILABLE = False
    
    # Dummy functions for fallback
    async def rag_query(query, chunks, model=None):
        return {
            "answer": "LLM RAG is not available. Showing raw search results instead.",
            "citations": [],
            "sources": [],
            "model_used": None,
            "error": True
        }
    
    async def rewrite_query_for_search(original_query, model=None):
        return original_query
from kb.ingest.web import extract_article
from kb.ingest.youtube import extract_transcript
from kb.ingest.twitter import extract_thread, extract_tweet_id
from kb.ingest.pdf import extract_pdf
from kb.summarize import summarize_article, format_summary_for_discord
import config

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')


async def ingest_url(url: str, channel: discord.TextChannel) -> Optional[dict]:
    """Ingest a URL and store in knowledge base. Returns dict with doc_id and content or None."""
    source_type = detect_source_type(url)
    result = None

    try:
        if source_type == 'youtube':
            result = extract_transcript(url)
        elif source_type == 'twitter':
            result = extract_thread(url)
            # If tweet contains article links, ingest those too
            if result and result.get('content'):
                linked_urls = URL_PATTERN.findall(result['content'])
                article_urls = [
                    u for u in linked_urls
                    if not any(x in u for x in ['t.co', 'twitter.com', 'x.com'])
                ]
                for article_url in article_urls[:3]:  # Max 3 linked articles
                    await channel.send(f"  ↳ Found linked article: `{article_url}` — ingesting...")
                    article_result = extract_article(article_url)
                    if article_result:
                        doc_id = process_and_store(
                            url=article_url,
                            source_type='article',
                            **article_result
                        )
                        await channel.send(f"  ↳ ✅ Article ingested (doc #{doc_id})")
        elif source_type == 'article':
            result = extract_article(url)

        if not result:
            return None

        doc_id = process_and_store(
            url=url,
            source_type=source_type,
            **result
        )
        return {'doc_id': doc_id, 'title': result.get('title', 'Untitled'), 'content': result.get('content', '')}

    except Exception as e:
        print(f"Error ingesting {url}: {e}")
        await channel.send(f"❌ Error ingesting `{url}`: {str(e)[:100]}")
        return None


@bot.event
async def on_ready():
    """Initialize DB and report readiness."""
    init_db()
    print(f"Knowledge base bot online: {bot.user}")
    channel = bot.get_channel(config.KB_CHANNEL_ID)
    if channel:
        await channel.send("📚 Knowledge base bot online. Drop URLs here to ingest them.")


@bot.event
async def on_message(message: discord.Message):
    """Process messages in the KB channel."""
    if message.author.bot:
        return

    # Only process messages in the KB channel
    if message.channel.id != config.KB_CHANNEL_ID:
        await bot.process_commands(message)
        return

    # Handle PDF attachments
    for attachment in message.attachments:
        if attachment.filename.lower().endswith('.pdf'):
            async with message.channel.typing():
                status = await message.channel.send(f"📄 Processing PDF: `{attachment.filename}`...")
                pdf_bytes = await attachment.read()
                result = extract_pdf(pdf_bytes, attachment.filename)

                if result:
                    doc_id = process_and_store(
                        url=f"discord://attachment/{message.id}/{attachment.filename}",
                        source_type='pdf',
                        **result
                    )
                    await status.edit(content=f"✅ PDF ingested: **{result['title']}** (doc #{doc_id})")
                else:
                    await status.edit(content=f"❌ Could not extract text from `{attachment.filename}`")

    # Handle commands
    if message.content.startswith('!'):
        await bot.process_commands(message)
        return

    # Detect and ingest URLs in message
    urls = URL_PATTERN.findall(message.content)
    if not urls:
        return

    for url in urls:
        source_type = detect_source_type(url)
        emoji = {'youtube': '🎬', 'twitter': '🐦', 'pdf': '📄', 'article': '📰'}.get(source_type, '🔗')
        status = await message.channel.send(f"{emoji} Ingesting `{url}`...")

        async with message.channel.typing():
            ingest_result = await ingest_url(url, message.channel)

        if ingest_result:
            doc_id = ingest_result['doc_id']
            title = ingest_result['title']
            content = ingest_result['content']
            await status.edit(content=f"{emoji} ✅ Ingested: `{url}` (doc #{doc_id})")
            
            # Generate and post summary for articles
            if source_type == 'article' and content:
                try:
                    summary = await asyncio.to_thread(summarize_article, content, title)
                    if summary:
                        summary_msg = format_summary_for_discord(title, summary, url)
                        await message.channel.send(summary_msg[:2000])  # Discord limit
                except Exception as e:
                    print(f"Summary generation failed: {e}")
                    # Don't fail ingestion if summary fails
        else:
            await status.edit(content=f"❌ Could not ingest: `{url}`")


@bot.command(name='ask', aliases=['q', 'query'])
async def ask_command(ctx: commands.Context, *, query: str):
    """Query the knowledge base with natural language using LLM RAG."""
    if ctx.channel.id != config.KB_CHANNEL_ID:
        return

    # Send initial status
    status_msg = await ctx.send("🔍 Searching knowledge base...")

    try:
        async with ctx.typing():
            # Optional: rewrite query for better search
            search_query = await rewrite_query_for_search(query)
            if search_query != query:
                await status_msg.edit(content=f"🔍 Searching (optimized: `{search_query}`)...")
            
            # Retrieve relevant chunks
            results = hybrid_search(search_query, limit=5)

            if not results:
                await status_msg.edit(content="📭 Knowledge base is empty. Try ingesting some URLs first with `!help` for instructions.")
                return

            # Flatten chunks for RAG
            all_chunks = []
            for result in results:
                for chunk in result.get('chunks', []):
                    all_chunks.append({
                        **chunk,
                        'url': result['url'],
                        'title': result.get('title', 'Untitled'),
                        'source_type': result['source_type']
                    })

            await status_msg.edit(content=f"🧠 Synthesizing answer from {len(all_chunks)} chunks...")

            # Generate LLM answer
            rag_result = await rag_query(query, all_chunks[:8])  # Top 8 chunks max

        # Build response embed
        embed = discord.Embed(
            title=f"💡 Answer",
            description=rag_result['answer'][:4000],
            color=discord.Color.blue()
        )

        # Add sources
        if rag_result.get('sources'):
            source_lines = []
            for i, src in enumerate(rag_result['sources'][:5], 1):
                emoji = {'youtube': '🎬', 'twitter': '🐦', 'pdf': '📄', 'article': '📰'}.get(
                    src['source_type'], '🔗'
                )
                title = src['title'][:50] + '...' if len(src['title']) > 50 else src['title']
                source_lines.append(f"[{i}] {emoji} [{title}]({src['url']})")
            
            embed.add_field(
                name="📚 Sources",
                value='\n'.join(source_lines),
                inline=False
            )

        # Add metadata footer
        model = rag_result.get('model_used', 'unknown')
        embed.set_footer(text=f"Model: {model} | Query: {query[:50]}...")

        await status_msg.delete()
        await ctx.send(embed=embed)
        
    except Exception as e:
        import traceback
        print(f"Error in ask_command: {e}")
        print(traceback.format_exc())
        await status_msg.edit(content=f"❌ Error processing query: {str(e)[:200]}")


@bot.command(name='search', aliases=['s'])
async def search_command(ctx: commands.Context, *, query: str):
    """Semantic search for relevant chunks (raw results, no LLM)."""
    if ctx.channel.id != config.KB_CHANNEL_ID:
        return

    async with ctx.typing():
        results = hybrid_search(query, limit=5)

    if not results:
        await ctx.send("🔍 No results found.")
        return

    embed = discord.Embed(
        title=f"🔍 Search Results: *{query}*",
        color=discord.Color.blue()
    )

    for i, result in enumerate(results, 1):
        source_emoji = {'youtube': '🎬', 'twitter': '🐦', 'pdf': '📄', 'article': '📰'}.get(
            result['source_type'], '🔗'
        )
        title = result.get('title') or result['url']
        if len(title) > 60:
            title = title[:57] + '...'

        # Build chunk preview
        chunk_preview = ""
        if result.get('chunks'):
            top_chunk = result['chunks'][0]['content']
            chunk_preview = top_chunk[:200] + '...' if len(top_chunk) > 200 else top_chunk

        score_bar = f"Score: `{result['score']:.3f}`"

        embed.add_field(
            name=f"{i}. {source_emoji} {title}",
            value=f"{score_bar}\n{chunk_preview}\n<{result['url']}>",
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command(name='entity')
async def entity_command(ctx: commands.Context, *, entity_name: str):
    """Find all documents mentioning an entity."""
    if ctx.channel.id != config.KB_CHANNEL_ID:
        return

    async with ctx.typing():
        results = search_by_entity(entity_name, limit=5)

    if not results:
        await ctx.send(f"🔍 No documents found mentioning **{entity_name}**.")
        return

    embed = discord.Embed(
        title=f"🏷️ Documents mentioning: *{entity_name}*",
        color=discord.Color.green()
    )
    for result in results:
        source_emoji = {'youtube': '🎬', 'twitter': '🐦', 'pdf': '📄', 'article': '📰'}.get(
            result['source_type'], '🔗'
        )
        title = result.get('title') or result['url']
        embed.add_field(
            name=f"{source_emoji} {title[:60]}",
            value=f"<{result['url']}>",
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command(name='recent')
async def recent_command(ctx: commands.Context, n: int = 5):
    """Show recently ingested documents."""
    if ctx.channel.id != config.KB_CHANNEL_ID:
        return

    from kb.database import get_recent_documents
    results = get_recent_documents(limit=min(n, 10))

    if not results:
        await ctx.send("📭 No documents ingested yet.")
        return

    embed = discord.Embed(title="📚 Recently Ingested", color=discord.Color.purple())
    for result in results:
        source_emoji = {'youtube': '🎬', 'twitter': '🐦', 'pdf': '📄', 'article': '📰'}.get(
            result['source_type'], '🔗'
        )
        title = result.get('title') or result['url']
        ingested = result['ingested_at'][:10] if result.get('ingested_at') else 'unknown'
        embed.add_field(
            name=f"{source_emoji} {title[:55]}",
            value=f"Ingested: {ingested} | <{result['url']}>",
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command(name='stats')
async def stats_command(ctx: commands.Context):
    """Show knowledge base statistics."""
    if ctx.channel.id != config.KB_CHANNEL_ID:
        return

    stats = get_stats()

    embed = discord.Embed(title="📊 Knowledge Base Stats", color=discord.Color.gold())
    embed.add_field(name="Total Documents", value=str(stats['total_documents']), inline=True)
    embed.add_field(name="Total Chunks", value=str(stats['total_chunks']), inline=True)
    embed.add_field(name="Total Entities", value=str(stats['total_entities']), inline=True)

    if stats.get('by_source'):
        source_lines = []
        for src, count in stats['by_source'].items():
            emoji = {'youtube': '🎬', 'twitter': '🐦', 'pdf': '📄', 'article': '📰'}.get(src, '🔗')
            source_lines.append(f"{emoji} {src}: {count}")
        embed.add_field(name="By Source", value='\n'.join(source_lines), inline=False)

    await ctx.send(embed=embed)


@bot.command(name='help')
async def help_command(ctx: commands.Context):
    """Show help message."""
    if ctx.channel.id != config.KB_CHANNEL_ID:
        return

    embed = discord.Embed(
        title="📚 Knowledge Base — Help",
        description="Drop URLs in this channel to auto-ingest them. Upload PDFs directly.",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="Supported Sources",
        value="📰 Articles (any URL)\n🎬 YouTube (auto-transcript)\n🐦 X/Twitter (full threads)\n📄 PDFs (upload file)",
        inline=False
    )
    embed.add_field(
        name="Commands",
        value=(
            "`!ask <query>` — LLM-powered RAG answer\n"
            "`!search <query>` — Raw semantic search results\n"
            "`!entity <name>` — Find docs by entity\n"
            "`!recent [n]` — Show recent ingestions\n"
            "`!stats` — Database statistics\n"
            "`!help` — This message"
        ),
        inline=False
    )
    embed.add_field(
        name="How Ranking Works",
        value="Results ranked by: semantic similarity + keyword match + recency boost + source weight",
        inline=False
    )
    await ctx.send(embed=embed)


if __name__ == '__main__':
    if not config.DISCORD_BOT_TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN not set in .env")
    bot.run(config.DISCORD_BOT_TOKEN)

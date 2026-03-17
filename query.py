#!/usr/bin/env python3
"""
CLI for querying the knowledge base directly (without Discord).
Usage:
    python query.py "What are the key ideas in my notes about AI?"
    python query.py --recent 5
    python query.py --entity "Sam Altman"
    python query.py --stats
"""
import sys
import argparse
from kb.database import init_db, get_stats, get_recent_documents
from kb.search import hybrid_search, search_by_entity


def print_result(i: int, result: dict):
    source_emoji = {'youtube': '🎬', 'twitter': '🐦', 'pdf': '📄', 'article': '📰'}.get(
        result.get('source_type', ''), '🔗'
    )
    title = result.get('title') or result.get('url', 'Untitled')
    print(f"\n{i}. {source_emoji} {title}")
    print(f"   URL: {result.get('url', 'N/A')}")
    print(f"   Score: {result.get('score', 0):.4f} | Semantic: {result.get('semantic_score', 0):.4f} | Keyword: {result.get('keyword_score', 0):.4f} | Recency: {result.get('time_score', 0):.4f}")

    if result.get('chunks'):
        chunk = result['chunks'][0]['content']
        preview = chunk[:300] + '...' if len(chunk) > 300 else chunk
        print(f"   Preview: {preview}")


def main():
    parser = argparse.ArgumentParser(description='Query the Personal Knowledge Base')
    parser.add_argument('query', nargs='?', help='Natural language query')
    parser.add_argument('--recent', type=int, metavar='N', help='Show N recent documents')
    parser.add_argument('--entity', type=str, help='Find docs mentioning entity')
    parser.add_argument('--stats', action='store_true', help='Show database stats')
    parser.add_argument('--limit', type=int, default=5, help='Max results (default: 5)')

    args = parser.parse_args()
    init_db()

    if args.stats:
        stats = get_stats()
        print("\n📊 Knowledge Base Statistics")
        print(f"  Documents: {stats['total_documents']}")
        print(f"  Chunks: {stats['total_chunks']}")
        print(f"  Entities: {stats['total_entities']}")
        if stats.get('by_source'):
            print("  By source:")
            for src, count in stats['by_source'].items():
                print(f"    {src}: {count}")

    elif args.recent:
        docs = get_recent_documents(limit=args.recent)
        print(f"\n📚 {len(docs)} Most Recent Documents")
        for i, doc in enumerate(docs, 1):
            source_emoji = {'youtube': '🎬', 'twitter': '🐦', 'pdf': '📄', 'article': '📰'}.get(
                doc.get('source_type', ''), '🔗'
            )
            title = doc.get('title') or doc.get('url', 'Untitled')
            print(f"\n{i}. {source_emoji} {title}")
            print(f"   {doc.get('url', 'N/A')}")
            print(f"   Ingested: {doc.get('ingested_at', 'unknown')}")

    elif args.entity:
        results = search_by_entity(args.entity, limit=args.limit)
        print(f"\n🏷️ Documents mentioning: '{args.entity}'")
        if not results:
            print("  No results found.")
        for i, doc in enumerate(results, 1):
            source_emoji = {'youtube': '🎬', 'twitter': '🐦', 'pdf': '📄', 'article': '📰'}.get(
                doc.get('source_type', ''), '🔗'
            )
            title = doc.get('title') or doc.get('url', 'Untitled')
            print(f"\n{i}. {source_emoji} {title}")
            print(f"   {doc.get('url', 'N/A')}")

    elif args.query:
        results = hybrid_search(args.query, limit=args.limit)
        print(f"\n🔍 Results for: '{args.query}'")
        if not results:
            print("  No results found.")
        for i, result in enumerate(results, 1):
            print_result(i, result)

    else:
        # Interactive mode
        print("📚 Personal Knowledge Base — Interactive Mode")
        print("Type 'exit' to quit, '!recent', '!stats', or any query.\n")
        while True:
            try:
                query = input("Query> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if not query:
                continue
            if query.lower() in ('exit', 'quit', 'q'):
                print("Bye!")
                break
            if query == '!recent':
                docs = get_recent_documents(5)
                for i, doc in enumerate(docs, 1):
                    print(f"{i}. {doc.get('title') or doc.get('url', 'N/A')}")
                continue
            if query == '!stats':
                stats = get_stats()
                print(f"Docs: {stats['total_documents']} | Chunks: {stats['total_chunks']} | Entities: {stats['total_entities']}")
                continue

            results = hybrid_search(query, limit=5)
            if not results:
                print("No results.\n")
            for i, result in enumerate(results, 1):
                print_result(i, result)
            print()


if __name__ == '__main__':
    main()

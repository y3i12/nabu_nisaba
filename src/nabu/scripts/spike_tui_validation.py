#!/usr/bin/env python3
"""
Phase 0 Spike: Validate TUI+Frames architecture.

Tests:
1. Load codebase root from kuzu
2. Expand python_root (lazy load children)
3. Verify children loaded correctly
4. Check memory usage
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from nabu.db.kuzu_manager import KuzuConnectionManager
from nabu.tui.frame_cache import FrameCache


def main():
    """Run spike validation."""
    print("=" * 60)
    print("Phase 0 Spike: TUI+Frames Architecture Validation")
    print("=" * 60)
    print()

    # Initialize database connection
    db_path = Path.cwd() / "nabu.kuzu"

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Run: nabu build-database")
        return 1

    print(f"✓ Database: {db_path}")
    print()

    db_manager = KuzuConnectionManager.get_instance(str(db_path))

    # Test 1: Initialize cache and load root
    print("Test 1: Initialize FrameCache and load codebase root")
    print("-" * 60)

    cache = FrameCache(db_manager)

    try:
        root = cache.initialize_root()
        print(f"✓ Loaded root: {root.name} ({root.qualified_name})")
        print(f"  Root has {len(root.children)} language children")

        for lang_root in root.children:
            print(f"    - {lang_root.name} ({lang_root.type.value})")

    except Exception as e:
        print(f"❌ Failed to load root: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print()

    # Test 2: Expand python_root (lazy load)
    print("Test 2: Expand python_root (lazy load children)")
    print("-" * 60)

    python_root = cache.get_or_load("nabu_nisaba.python_root")

    if not python_root:
        print("❌ python_root not found")
        return 1

    print(f"✓ Loaded python_root: {python_root.name}")
    print(f"  Children loaded before expand: {python_root._children_loaded}")
    print(f"  Children count: {python_root.get_child_count(db_manager)}")
    print()

    # Expand (lazy load children)
    python_root._view_expanded = True
    python_root.ensure_children_loaded(db_manager)

    print(f"  Children loaded after expand: {python_root._children_loaded}")
    print(f"  Actual children: {len(python_root.children)}")
    print()

    print("  First 5 children:")
    for child in python_root.children[:5]:
        print(f"    - {child.name} ({child.type.value}) - {child.qualified_name}")

    print()

    # Test 3: Verify cache
    print("Test 3: Verify frame caching")
    print("-" * 60)

    # Load same frame again - should return cached instance
    python_root_again = cache.get_or_load("nabu_nisaba.python_root")

    if python_root_again is python_root:
        print("✓ Cache hit: Same instance returned")
    else:
        print("❌ Cache miss: Different instance returned")

    print(f"  Total frames cached: {len(cache.frames)}")
    print()

    # Test 4: Memory usage
    print("Test 4: Memory usage estimation")
    print("-" * 60)

    import sys

    total_size = sum(sys.getsizeof(f) for f in cache.frames.values())
    print(f"  Total frames: {len(cache.frames)}")
    print(f"  Estimated memory: {total_size / 1024:.2f} KB")
    print()

    # Success
    print("=" * 60)
    print("✓ Spike validation successful!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

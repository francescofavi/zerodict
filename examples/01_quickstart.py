from zerodict import ZeroDict

if __name__ == "__main__":
    print("=" * 60)
    print("ZeroDict Usage Examples")
    print("=" * 60)

    # Example 1: Basic Creation and Dot Notation
    print("\n1. BASIC CREATION AND DOT NOTATION")
    print("-" * 60)

    ed = ZeroDict(
        {"user": {"name": "John", "age": 30}, "settings": {"theme": "light", "notifications": True}}
    )

    print("Created:")
    print(ed.to_json())
    print(f"\nUser name: {ed.user.name}")
    print(f"Theme: {ed.settings.theme}")

    # Safe reading - no side effects
    print(f"\nMissing field: {ed.optional}")  # None
    if ed.optional:
        print("This won't print")
    else:
        print("Missing fields return None (safe!)")

    # Example 2: Modifying Existing Paths
    print("\n2. MODIFYING EXISTING PATHS (Dot Notation)")
    print("-" * 60)

    ed.user.name = "Jane"
    ed.user.age = 31
    ed.settings.theme = "dark"

    print("After modifications:")
    print(ed.to_json())

    # Example 3: Creating Deep Paths with set_path
    print("\n3. CREATING DEEP PATHS (Path API)")
    print("-" * 60)

    # Create deeply nested structures in one call
    ed.set_path("database.host", "localhost")
    ed.set_path("database.port", 5432)
    ed.set_path("database.credentials.username", "admin")
    ed.set_path("database.credentials.password", "secret")

    ed.set_path("api.endpoints.users", "/api/v1/users")
    ed.set_path("api.endpoints.posts", "/api/v1/posts")
    ed.set_path("api.timeout", 30)

    print("After deep path creation:")
    print(ed.to_json())

    # Example 4: Array Access
    print("\n4. ARRAY ACCESS AND MANIPULATION")
    print("-" * 60)

    ed.set_path(
        "items",
        [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}, {"id": 3, "name": "Item 3"}],
    )

    print(f"First item: {ed.get_path('items[0]')}")
    print(f"First item name: {ed.get_path('items[0].name')}")
    print(f"Second item ID: {ed.get_path('items[1].id')}")

    # Modify array elements
    ed.set_path("items[0].price", 19.99)
    ed.set_path("items[1].price", 29.99)
    ed.set_path("items[2].price", 39.99)

    print("\nItems after adding prices:")
    for i in range(3):
        item = ed.get_path(f"items[{i}]")
        print(f"  {item}")

    # Example 5: Batch Updates (Atomic)
    print("\n5. BATCH UPDATES (Atomic - All or Nothing)")
    print("-" * 60)

    print("Before batch update:")
    print(f"  User: {ed.user.name}, Age: {ed.user.age}")

    ed.set_many(
        {
            "user.email": "jane@example.com",
            "user.verified": True,
            "user.role": "admin",
            "settings.language": "en",
            "settings.timezone": "UTC",
            "settings.notifications": False,
        }
    )

    print("\nAfter batch update:")
    print(f"  User: {ed.user.name}")
    print(f"  Email: {ed.user.email}")
    print(f"  Role: {ed.user.role}")
    print(f"  Language: {ed.settings.language}")

    # Example 6: Deep Diff for Change Tracking
    print("\n6. DIFF FOR CHANGE TRACKING")
    print("-" * 60)

    # Create original
    product = ZeroDict(
        {"name": "Product A", "price": 100, "stock": 50, "tags": ["electronics", "gadget"]}
    )

    print("Original product:")
    print(product.to_json())

    # Create modified version
    modified = ZeroDict.from_dict(product.to_dict())
    modified.price = 120
    modified.stock = 45
    modified.set_path("tags[1]", "device")
    modified.set_path("discount", 10)
    modified.delete_path("stock")

    print("\nModified product:")
    print(modified.to_json())

    # Calculate diff
    changes = product.diff(modified)
    print("\nChanges detected:")
    for change in changes:
        op = change["op"]
        path = change["path"]
        if op == "replace":
            print(f"  CHANGED {path}: {change['before']} → {change['after']}")
        elif op == "add":
            print(f"  ADDED {path}: {change['after']}")
        elif op == "remove":
            print(f"  REMOVED {path}: {change['before']}")

    # Example 7: JSON Round-trip
    print("\n7. JSON SERIALIZATION")
    print("-" * 60)

    config = ZeroDict(
        {
            "app": {"name": "MyApp", "version": "1.0.0", "debug": False},
            "features": {"analytics": True, "logging": True, "cache": False},
            "ports": [8000, 8001, 8002],
        }
    )

    # To JSON
    json_str = config.to_json()
    print("Serialized to JSON:")
    print(json_str)

    # From JSON
    loaded = ZeroDict.from_json(json_str)
    print(f"\nReloaded - App name: {loaded.app.name}")
    print(f"Reloaded - First port: {loaded.get_path('ports[0]')}")

    # Example 8: Dict-like Operations
    print("\n8. DICT-LIKE OPERATIONS")
    print("-" * 60)

    print(f"Number of top-level keys: {len(ed)}")
    print(f"'user' in ed: {'user' in ed}")
    print(f"'nonexistent' in ed: {'nonexistent' in ed}")

    print("\nTop-level keys:")
    for key in list(ed.keys())[:5]:  # First 5
        print(f"  - {key}")

    print("\nIterating over items (first 3):")
    for i, (key, value) in enumerate(ed.items()):
        if i >= 3:
            break
        value_type = type(value).__name__
        print(f"  {key}: {value_type}")

    # Example 9: Strict Mode
    print("\n9. STRICT MODE FOR VALIDATION")
    print("-" * 60)

    # Non-strict (default) - returns None
    result = ed.get_path("nonexistent.deep.path")
    print(f"Non-strict get on missing path: {result}")

    # Strict mode - raises exception
    try:
        ed.get_path("nonexistent.path", strict=True)
        print("This won't print")
    except KeyError as e:
        print(f"Strict mode raised KeyError: {e}")

    try:
        ed.set_path("missing.intermediate.path", "value", strict=True)
        print("This won't print")
    except KeyError as e:
        print(f"Strict set raised KeyError: {e}")

    # Example 10: Real-world Usage Pattern
    print("\n10. REAL-WORLD USAGE PATTERN")
    print("-" * 60)

    # Load config
    config_data = {
        "server": {"host": "0.0.0.0", "port": 8080},  # nosec B104
        "database": {"enabled": True, "url": "postgresql://localhost/mydb"},
    }

    config = ZeroDict(config_data)

    # Read with safety checks
    if config.database and config.database.enabled:
        print(f"Database is enabled: {config.database.url}")

    if config.cache:
        print("Cache config found")
    else:
        print("No cache config (returns None safely)")

    # Modify existing values
    config.server.port = 9000

    # Add new configuration sections
    config.set_path("logging.level", "INFO")
    config.set_path("logging.file", "/var/log/app.log")
    config.set_path("logging.rotate", True)

    # Batch update - creates new paths automatically
    config.set_many(
        {
            "features.api_v2": True,
            "features.websockets": False,
            "monitoring.enabled": True,
            "monitoring.interval": 60,
        }
    )

    print("\nFinal configuration:")
    print(config.to_json())

    # Use with default values
    cache_ttl = config.get_path("cache.ttl", default=3600)
    print(f"\nCache TTL (with default): {cache_ttl}")

    # Export for use elsewhere
    config_dict = config.to_dict()
    print(f"\nExported as dict, type: {type(config_dict)}")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)

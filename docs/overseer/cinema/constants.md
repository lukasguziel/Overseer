# cinema/constants

The one place for c4d-bound constant tables — kept out of [core/defaults](../core/defaults.md)
because it imports `c4d` and therefore may not be loaded by the pure unit tests.

## Constants
- `KNOWN_TYPES` — maps a c4d object type id (`c4d.Onull`, `c4d.Ocamera`, MoGraph ids, …) to a friendly type name. Used by the adapter's `type_name()` before falling back to `GetTypeName()`.

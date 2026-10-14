"""Compatible alias preserving the Antigravity registry and module entrypoint."""

import sys

from . import host_hook
from .host_hook import (
    DEFAULTS as DEFAULTS,
)
from .host_hook import (
    ENV as ENV,
)
from .host_hook import (
    MAX_BINDINGS as MAX_BINDINGS,
)
from .host_hook import (
    MAX_DB_BYTES as MAX_DB_BYTES,
)
from .host_hook import (
    REQUIRED as REQUIRED,
)
from .host_hook import (
    SERVER as SERVER,
)
from .host_hook import (
    TTL as TTL,
)
from .host_hook import (
    BindingError as BindingError,
)
from .host_hook import (
    Bindings as Bindings,
)
from .host_hook import (
    hook as hook,
)
from .host_hook import (
    main as main,
)
from .host_hook import (
    normalized as normalized,
)
from .host_hook import (
    private_file as private_file,
)

if __name__ == "__main__":
    main()
else:
    # Preserve callers that override registry constants through the historic module.
    sys.modules[__name__] = host_hook

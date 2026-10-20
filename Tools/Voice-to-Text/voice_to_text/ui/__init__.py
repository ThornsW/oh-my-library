"""GTK 3 user interface. GTK 3 (not 4) because the floating window needs
keep-above and no-focus, which GTK 4 removed."""

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")

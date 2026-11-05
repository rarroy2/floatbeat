"""Entry point: ``python -m floatbeat`` or the ``floatbeat`` console script."""

from __future__ import annotations

import argparse
import signal
import sys
from collections.abc import Sequence

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="floatbeat",
        description="A tiny floating DJ for the Linux desktop.",
    )
    parser.add_argument(
        "--no-demo",
        action="store_true",
        help="start paused in the resting pose (useful to measure idle cost)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args, qt_args = build_parser().parse_known_args(argv)

    # Must happen before QApplication exists: the platform plugin is chosen
    # when the application object is created.
    from .desktop.display import prefer_xwayland

    prefer_xwayland()

    from PySide6.QtWidgets import QApplication

    from .app import FloatbeatApp

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Floatbeat")
    app.setApplicationDisplayName("Floatbeat")
    app.setOrganizationName("Floatbeat")
    app.setOrganizationDomain("github.com/rarroy2")
    app.setDesktopFileName("io.github.rarroy2.Floatbeat")

    # Let Ctrl+C in a terminal close the app instead of being swallowed by Qt.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    controller = FloatbeatApp(app)
    controller.start(paused=args.no_demo)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

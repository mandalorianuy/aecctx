# Optional PDF and Image Dependencies

AECCTX uses `pypdf>=6.6,<7` under BSD-3-Clause for PDF structure/content evidence and `Pillow>=12.1,<13` under MIT-CMU for image validation and decoded PDF raster artifacts.

They are separately installed through the `aecctx[pdf]` and `aecctx[image]` extras and are not bundled into the Apache-2.0 core wheel. No AGPL/GPL PDF decoder is linked into the core or these adapters.

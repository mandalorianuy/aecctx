# ACX-18 acceptance evidence

Status: in progress; replay and claim evidence cut

The exact experimental profile is self-contained R2000/`AC1015` through `org.aecctx.dwg.libredwg@0.2.0`, Linux arm64 live image `sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1`, plus portable offline replay.

Committed replay binds source DWG `fe9e07cabc83eb99c3c2334d5503fbcc9ebe0f94d349581ee559d57d6a30c494`, canonical LibreDWG JSON `190545218aed4766e0d477720362098f56c41f9279c200cd2750a5674bd32183` and converted DXF `9f86d16181606a3deb2e8ae1f5a1cb95c68885e2ee3e83d180940732d9a92ffc`.

The claim is partial: direct JSON objects are observed decoder evidence; DXF and normalized geometry are converted/derived. Duplicate handles remain conflicted. Units/CRS, complete 3D, ACIS/proxy/custom semantics, xref traversal and every DWG version other than AC1015 remain unsupported or unknown.

Final repository gates, CI run and completion promotion are recorded only after Task 5 passes.

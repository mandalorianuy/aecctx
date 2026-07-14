# Optional IfcTester Dependency and Official IDS Fixtures

The ACX-21 and ACX-36 gate profiles use the separately distributed `ifctester==0.8.5` package with `ifcopenshell==0.8.5`. Installed distribution metadata identifies both as LGPL-3.0-or-later. They remain optional through `aecctx[gate-ids]`; neither distribution nor native runtime is bundled into the Apache-2.0 core wheel.

The unchanged official ACX-36 IDS/IFC inputs come from buildingSMART IDS release `v1.0.0`, final commit `1effec6f419798ce09617416d258a35bdc58320a`, under CC BY-ND 4.0. Their repository paths and SHA-256 digests are recorded in `fixtures/v0.3/gate/official/ORIGIN.json`, alongside the retained license text. Project-authored cases are generated separately under Apache-2.0 and never presented as official buildingSMART cases.

Distributors installing the optional evaluator or redistributing official fixtures remain responsible for the applicable license and notice obligations. A different dependency version or modified official fixture is outside the public claim until a governed conformance and licensing review passes.

"""Phase 6A federated learning backend integration (read-only status mirror).

This package exposes the latest on-demand federated run to the dashboard/API by
reading the artifacts written by ``apps.learning.federated.runner``. It does NOT
launch training — there is no always-on background process (item 13).
"""

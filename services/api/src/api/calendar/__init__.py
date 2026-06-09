"""Calendar Assembly module — Step 2.4.

Composes day/week/month/year/range views from:
  - cached Panchang (Step 1.4)
  - resolved festivals/vrats (Step 2.2)
  - user overlays (notes, bookmarks, reminders — stubbed until later steps)

Returns fully view-ready payloads. Clients perform no Panchang math.
"""

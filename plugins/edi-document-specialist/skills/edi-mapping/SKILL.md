---
name: edi-mapping
description: X12 EDI segment references with field-to-template variable mappings. Use when mapping EDI document fields to CRE2 PDF templates or understanding X12 segment structures (810, 850, 855, 856, 860).
triggers:
  keywords:
    - x12
    - edi segment
    - 810 invoice
    - 850 purchase order
    - 855 acknowledgment
    - 856 ship notice
    - 860 change
    - BIG segment
    - N1 segment
    - IT1 segment
    - ITD segment
    - TDS segment
---

# EDI Mapping Skill

X12 EDI segment references with field-to-template variable mappings for CRE2 PDF templates.

## Resources

- [810 Invoice Segments](resources/x12-segments-810.md)
- [850 Purchase Order Segments](resources/x12-segments-850.md)
- [855 PO Acknowledgment Segments](resources/x12-segments-855.md)
- [856 Ship Notice Segments](resources/x12-segments-856.md)
- [860 PO Change Segments](resources/x12-segments-860.md)

## Examples

**What fields are in an 810 invoice header?**
Reference x12-segments-810.md for BIG segment mappings.

**How do I map the invoice total to a template?**
TDS01 segment maps to invoiceSummary.totalAmount (divide by 100).

**Where is the PO number in an 810?**
BIG04 maps to invoiceSummary.poNumber.

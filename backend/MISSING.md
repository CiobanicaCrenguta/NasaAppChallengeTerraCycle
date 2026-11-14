# What is still missing from the crop table

Everything below is `null` in `crops.json`, or is there with status `de_confirmat`. The engine must skip a `null` and must not present a `de_confirmat` value as a fact. Source ids are in `SOURCES.md`.

## Null: no source found

| Crop | Parameter | What we looked at |
|---|---|---|
| Peas (spring) | Sowing window | Fundulea variety sheets give a window only for autumn peas (S15). The sheet for the spring variety Nicoleta gives the growing period (78–96 days) but no sowing date. No second Romanian source found. |
| Peas | Heat at flowering, both levels | Not in S9–S12. AquaCrop 7.3 has no pea file. |
| Sugar beet | Everything | The crop is not in the table yet. One web search found no guide from the sugar beet institute (INCDSZ Brașov); only weather bulletins and press, which we do not use. No break interval in S6 or S7. |
| Wheat | Years between wheat crops | S1 only says wheat may follow wheat for one year in extreme cases. No figure for the normal break. |
| Barley | Years between barley crops | S1 only says barley may follow wheat. |
| Corn | Years between corn crops | No figure. S7 calls corn "self-tolerant". |
| Soybean | Years between soybean crops | No figure in S1, S6 or S7. S6 gives 3 years between sunflower and soybean, stored under sunflower. |
| Sunflower | Heat at flowering, "attention" level | Only the AquaCrop "loss" level (S12). |
| Barley | Heat at flowering, "attention" level | Only the AquaCrop "loss" level (S12). |
| Rapeseed | Heat at flowering, "loss" level | AquaCrop 7.3 has no rapeseed file. |
| Winter barley | Lengths of growth stages | FAO-56 Table 11 (S13) has no row for winter barley. |
| Winter rapeseed | Lengths of growth stages | FAO-56 Table 11 (S13) has no row for rapeseed. |
| Corn, soybean | Killing temperatures | Empty in ECOCROP (S14). |
| Corn | Soil texture | Empty in the ECOCROP record for *Zea mays* (S14). |

Not looked for in this step: harvest dates, nitrogen left in the soil by peas and soybean, and the water a crop takes from the soil.

## Present but `de_confirmat`

| Crop | Parameter | Value | Why it is not confirmed |
|---|---|---|---|
| Corn | Sowing window | 1 April, 15 April, 1 May tested; best mean at 15 April (S4) | The figures were read in S4, but it is a trial result, not a recommendation. |
| Peas | Years between Aphanomyces-sensitive legumes | 6 (S8, p. 37) | The file could not be opened (server error 522). |
| Soybean | Heat at flowering, "attention" | 30–35 °C (S9, §1.2) | Only the DOAJ record was read, not the full text. |
| Wheat | Heat at flowering, "attention" | 31 °C (S10, Table 1) | The figure is in S10 as printed, but it comes from Porter and Gawith (1999), which was not opened. It is a cardinal temperature for the anthesis phase, not a rule about daily maximum temperature. |

## Weak points in confirmed values

- **Growth-stage lengths (S13)** are for Idaho, the Mediterranean and the central USA. They are confirmed as printed, but they are not Romanian values.
- **Rotation gaps for sunflower and rapeseed (S6)** come from a guide for organic farming, in its edition for the Republic of Moldova.
- **Rapeseed heat threshold (S11)** is from a review table that cites another paper.
- **S1** was read in a copy hosted by a town hall; the original on madr.ro or asas.ro was not found.
- **S7** is a seed company's advisory page.
- **AquaCrop values (S12)** for maize, soybean and wheat are marked "Estimate" by their authors.
- **ECOCROP (S14)** was read in a copy published on GitHub, not on FAO's site.

# Metsanduswidget'i ligipääsetavuse lokaalne audit

- Kuupäev: 2026-08-16
- Siht: `static/embed/index.html`
- Tulemus: **LÄBITUD**
- Tase: WCAG 2.2 AA local prototype contract

## Struktuur ja käitumisleping

| Kontroll | Tulemus | Tõend |
|---|---|---|
| `document_language` | ✓ | <html lang="et"> |
| `single_labelled_main` | ✓ | Üks main-landmark on seotud nähtava H1-ga. |
| `question_name_and_description` | ✓ | Textarea nimi tuleb label'ist ja juhis aria-describedby kaudu. |
| `live_status_and_alert` | ✓ | Asünkroonne olek ja vead on eraldi live-region'ites. |
| `result_focus_target` | ✓ | Tulemuse kuvamisel liigub fookus programmiliselt vastuse H2-le. |
| `form_busy_and_invalid_state` | ✓ | Laadimine ja lokaalne valideerimisviga jõuavad accessibility API-sse. |
| `label_references_resolve` | ✓ | Kõik aria-labelledby IDREF-id lahenevad samas dokumendis. |
| `unique_ids` | ✓ | Dokumendis ei ole korduvaid id atribuute. |
| `logical_heading_order` | ✓ | Pealkirjatasemed DOM-is: [1, 2, 2, 2, 3, 3]. |
| `no_positive_tabindex` | ✓ | Tabijärjekord järgib DOM-i; positiivseid tabindex väärtusi pole. |
| `visible_focus_contract` | ✓ | 3 px kõrge kontrastiga väline fookusrõngas kõigil interaktiivsetel elementidel. |
| `reduced_motion_contract` | ✓ | Vähendatud liikumise kasutajaeelistus on CSS-is toetatud. |
| `responsive_and_target_size_contract` | ✓ | Mobiilipaigutus ja 44 px põhitoimingu kõrgus on määratud. |

## Kontrast

| Paar | Suhe | Miinimum | Tulemus |
|---|---:|---:|---|
| body text (`#17332d` / `#f2f6f1`) | 12.42:1 | 4.5:1 | ✓ |
| primary heading (`#123f34` / `#ffffff`) | 11.76:1 | 4.5:1 | ✓ |
| lead text (`#46615b` / `#ffffff`) | 6.73:1 | 4.5:1 | ✓ |
| review status text (`#6b4e13` / `#f2f6f1`) | 7.06:1 | 4.5:1 | ✓ |
| secondary text (`#61736e` / `#ffffff`) | 5.02:1 | 4.5:1 | ✓ |
| placeholder text (`#61736e` / `#fbfdfb`) | 4.91:1 | 4.5:1 | ✓ |
| primary button text (`#ffffff` / `#176a56`) | 6.50:1 | 4.5:1 | ✓ |
| question chip text (`#245348` / `#f6faf7`) | 8.29:1 | 4.5:1 | ✓ |
| request status (`#526b64` / `#f2f6f1`) | 5.27:1 | 4.5:1 | ✓ |
| error text (`#78281f` / `#fff1ef`) | 8.99:1 | 4.5:1 | ✓ |
| confidence text (`#34554d` / `#e9f1ed`) | 7.16:1 | 4.5:1 | ✓ |
| clarification text (`#573f10` / `#fff6dd`) | 9.17:1 | 4.5:1 | ✓ |
| source link (`#0e604c` / `#ffffff`) | 7.51:1 | 4.5:1 | ✓ |
| footer text (`#60736d` / `#f2f6f1`) | 4.61:1 | 4.5:1 | ✓ |
| textarea boundary (`#748f84` / `#fbfdfb`) | 3.42:1 | 3.0:1 | ✓ |
| chip boundary (`#7b9489` / `#f6faf7`) | 3.10:1 | 3.0:1 | ✓ |
| focus ring on card (`#7a4a00` / `#ffffff`) | 7.48:1 | 3.0:1 | ✓ |
| focus ring on page (`#7a4a00` / `#f2f6f1`) | 6.85:1 | 3.0:1 | ✓ |

## Piirangud

- Static checks do not emulate a named screen reader or browser/OS combination.
- Keyboard and accessibility-tree smoke evidence is recorded separately in docs/kaur/accessibility-qa.md.
- Independent WCAG conformance review remains a pre-publication KAUR gate.

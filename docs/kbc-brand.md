# KBC brand reference

Source: the public KBC Design Language (KDL) token stylesheet served by kbc.be
(`kdl-design-tokens.latest.min.css`), read on 2026-09-30. Use these values, not guesses.

## Colours

| Role in KBC Fit | KDL token | Value |
|---|---|---|
| Main text, headers, night blue | `--kdl-color-primary-main` | `#0D2A50` (rgb 13,42,80) |
| Darker night blue (pressed states) | `--kdl-color-primary-main-600` | `#021E43` |
| Secondary text | `--kdl-color-primary-main-300` | `#45658F` |
| Disabled text | `--kdl-color-primary-main-200` | `#7394C2` |
| Borders, dividers | `--kdl-color-primary-main-100` | `#BFDAFF` |
| Light tint of main | `--kdl-color-primary-main-25` | `#EFF6FF` |
| CTA, links, goal ring | `--kdl-color-primary-accent` | `#0097DB` (rgb 0,151,219) |
| Accent hover/pressed | `--kdl-color-primary-accent-600` | `#007AB1` |
| Accent tint | `--kdl-color-primary-accent-100` | `#E5F4FF` |
| Page / app background | `--kdl-color-surface-background` | `#F2F2F2` |
| Element background (chips, info blocks) | `--kdl-color-surface-element` | `#F2FAFF` |
| Cards | `--kdl-color-elevation-01` | `#FFFFFF` |
| Kate (assistant) | `--kdl-color-os-kate` | `#55C7DF` |
| Secondary 01 (teal) | `--kdl-color-secondary-01` | `#008571` |
| Secondary 02 (yellow) | `--kdl-color-secondary-02` | `#E9C100` |
| Secondary 03 (pink) | `--kdl-color-secondary-03` | `#EE7079` |
| Success | `--kdl-color-system-success` | `#5BA215` (tint `#EEFFE4`) |
| Warning | `--kdl-color-system-warning` | `#DC7507` (tint `#FFF7F1`) |
| Error | `--kdl-color-system-error` | `#D64040` (tint `#FFF6F5`) |
| Modal overlay | `--kdl-color-overlay-default` | `rgba(13,42,80,0.4)` |
| Shadow colour | `--kdl-color-shadow-default` | `rgba(0,0,0,0.16)` |

## Shape and depth (from kbc.be main stylesheet)

- Card radius: `8px`. Small elements (inputs, chips): `4px`.
- Buttons: pill, `border-radius: 100px`.
- Card shadow: `0 4px 16px rgba(0,54,101,.08)`; raised: `0 4px 16px rgba(0,54,101,.16)`.

## Typography

- KBC uses **Museo Sans** (weights 300, 500, 700).
- Museo Sans is a **commercial font**: never commit the font files to this public repo.
- Stack: `"MuseoSans", "Museo Sans", "Nunito Sans", system-ui, sans-serif`.
  Nunito Sans (free, loaded with `next/font`) is the fallback.

## Logo

- Official KBC logo: `public/brand/kbc-logo.svg` (from the KDL asset library on kbc.be).
- Rendered only through one `<KbcLogo />` component so it is easy to swap or remove.
- Colours in the logo: accent `#0097DB` and night blue `#0D2A50`.

## Rules

- Reproduce the style in code. **No screenshots of the real KBC app** in the repo, video or Builderbase.
- All customer data stays 100% synthetic.
- Footer mention: "Built for the KBC challenge at Tectonic Hackathon".

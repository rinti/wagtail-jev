# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `BoundTagField.score(article)`: a probability for every candidate tag, unfiltered and sorted high to low. `suggest()` is `score()` with the threshold and cap applied.
- `wagtail_jev.models` exports `PromptTemplates` and `TagSuggestion`.

### Changed

- README rewritten in plainer language: shorter sentences, a lead-in for every code example, and fuller descriptions in the settings table.
- `PromptTemplates` and `TagSuggestion` live in `wagtail_jev.tag_field`. Import them from there or from `wagtail_jev.models`.
- `get_client()` lives in `wagtail_jev.client`, alongside `ask()`, which sends one request and owns the connection's lifetime, and `clip()`, which applies `WAGTAIL_JEV_MAX_CHARS`. Tag fields and Qualities no longer open or close connections themselves.
- Requests are logged once as "jev answered N questions" instead of separately per tag field and Quality.

### Removed

- `wagtail_jev.classifier`. Its `score_tags()` is now `BoundTagField.score()`; `build_state()` and `build_question()` are implementation details of the Tag field.

## [0.3.0] - 2026-09-19

### Added

- `Quality` and `Level` (`wagtail_jev.quality`): an ordered rubric of two to ten levels Jev rates a text on, each level a short label for the editor and a concrete description for Jev. Declared under a key in `JevTaggableMixin.jev_qualities`; `Quality.label` is the display name and falls back to the key. Each Quality is one Score question.
- `Rating` (`wagtail_jev.quality`): the most likely level, the argmax of the per-level probabilities, plus a probability for every level. Shown, never saved; not gated by any threshold.
- `Excerpt` (`wagtail_jev.article`): the flattened text of one field, with no title and no tags, built from a saved page (`Excerpt.from_page`) or from unsaved edit-form data (`Excerpt.from_form_data`).
- `JevTaggableMixin.jev_quality(key)` returns the bound Quality and `jev_bound_qualities(*keys)` the bound Qualities in declaration order. A bound Quality's `rate()` takes an Article or an Excerpt.
- `page.jev_rate(*keys)` and `wagtail_jev.quality.rate()` rate every requested Quality in one Jev request.
- `JevRatingPanel` (`wagtail_jev.panels`): a "Rate with Jev" button that rates the editor's unsaved Article on all or some Qualities.
- `JevRatingFieldPanel` (`wagtail_jev.panels`): a `FieldPanel` for a `RichTextField`, `StreamField`, `CharField` or `TextField` with a "Rate with Jev" button that rates just that field's Excerpt on the given Quality keys.
- Both rating panels name the Quality on the button when exactly one is attached.
- Admin endpoint `wagtail_jev:rate` returns the Ratings for the posted edit form; with `jev_field` it rates that field's Excerpt instead of the Article. Each Rating carries `key`, `label`, the top level and every level's probability.
- Qualities share `WAGTAIL_JEV_MODEL`, `WAGTAIL_JEV_API_KEY`, `WAGTAIL_JEV_TIMEOUT` and `WAGTAIL_JEV_MAX_CHARS` with tagging; no new settings, no migration.
- `BoundTagField` (`wagtail_jev.tag_field`): one Tag field with settings resolved; `suggest(article)` runs the whole pipeline.
- `JevTaggableMixin.jev_tag_field()` returns the bound Tag field for a page model.

### Changed

- `Article.from_page()` and `Article.from_form_data()` no longer require a Tag field name; `from_form_data()` takes it as keyword `field_name`. An Article built for rating carries no existing tags.
- `jev_suggest_tags()` accepts only `client`; threshold and cap come from the Tag field.
- `score_tags()` and `build_question()` require `templates`.
- `JevTagField` lives in `wagtail_jev.tag_field`; `wagtail_jev.models` still exports it.

### Fixed

- Rich text posted from the editor is now read through the field's widget, so Draftail's contentstate JSON is flattened to text instead of being sent to Jev as-is. The `suggest` and `rate` endpoints expect a `RichTextField` value in the widget's format, as the editor posts it, not raw HTML.

### Removed

- `classifier.suggest_tags()`, `wagtail_jev.candidates`.
- `JevTaggableMixin.jev_tag_field_config()`, `jev_candidates()` and `jev_suggest_for_article()`.

## [0.2.0] - 2026-09-19

### Added

- `Article` (`wagtail_jev.article`): the title, body and existing tags Jev reads, built either from a saved page (`Article.from_page`) or from unsaved edit-form data (`Article.from_form_data`).
- `JevTaggableMixin.jev_suggest_for_article()`: the single pipeline from tag-field config to suggestions, shared by the admin endpoint, `jev_suggest_tags()` and the management command.

### Removed

- `wagtail_jev.text` and `wagtail_jev.forms`; their logic lives inside `Article`.
- `JevTaggableMixin.jev_text()`, `jev_existing_tags()` and `jev_add_tags()`.

## [0.1.0] - 2026-09-19

### Added

- Tag suggestions for Wagtail pages via Jev (TypeSafe System One), one Noul question per candidate tag.
- `JevTaggableMixin` with per-field `jev_tag_fields` configuration (`JevTagField`): prompts, candidates, threshold and cap per tag field.
- `JevTagFieldPanel`: tag widget with a "Let Jev suggest tags" button that scores the editor's unsaved content.
- `jev_tag_pages` management command with `--field`, `--apply` and `--publish`.
- `WAGTAIL_JEV_*` settings, including customizable prompt templates.

[Unreleased]: https://github.com/rinti/wagtail-jev/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/rinti/wagtail-jev/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rinti/wagtail-jev/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/rinti/wagtail-jev/releases/tag/v0.1.0

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `Quality` and `Level` (`wagtail_jev.quality`): an ordered rubric Jev rates an Article on, declared in `JevTaggableMixin.jev_qualities`.
- `page.jev_rate(*keys)` returns a `Rating` per Quality from one Jev request; `jev_quality(key)` returns the bound Quality.
- `JevRatingPanel` (`wagtail_jev.panels`): a "Rate with Jev" button that rates the editor's unsaved Article on all or some Qualities; Ratings are shown, never saved.
- `JevRatingFieldPanel` (`wagtail_jev.panels`): a `FieldPanel` for a `RichTextField`, `StreamField`, `CharField` or `TextField` with a "Rate with Jev" button that rates just that field's Excerpt on the given Quality keys. With one key the button names the Quality.
- `Excerpt` (`wagtail_jev.article`): the flattened text of one field, built from a saved page (`Excerpt.from_page`) or from unsaved edit-form data (`Excerpt.from_form_data`). A bound Quality's `rate()` takes an Article or an Excerpt.
- `Quality.label`: the display name editors see for a Quality; falls back to the key. Sent as `label` on every Rating.
- Admin endpoint `wagtail_jev:rate` returns the Ratings for the posted edit form; with `jev_field` it rates that field's Excerpt instead of the Article.
- `JevTaggableMixin.jev_bound_qualities(*keys)` returns the bound Qualities in declaration order.
- `BoundTagField` (`wagtail_jev.tag_field`): one Tag field with settings resolved; `suggest(article)` runs the whole pipeline.
- `JevTaggableMixin.jev_tag_field()` returns the bound Tag field for a page model.

### Changed

- `Article.from_page()` and `Article.from_form_data()` no longer require a Tag field name; `from_form_data()` takes it as keyword `field_name`.
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

[Unreleased]: https://github.com/rinti/wagtail-jev/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/rinti/wagtail-jev/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/rinti/wagtail-jev/releases/tag/v0.1.0

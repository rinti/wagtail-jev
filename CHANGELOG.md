# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `BoundTagField` (`wagtail_jev.tag_field`): one Tag field with settings resolved; `suggest(article)` runs the whole pipeline.
- `JevTaggableMixin.jev_tag_field()` returns the bound Tag field for a page model.

### Changed

- `jev_suggest_tags()` accepts only `client`; threshold and cap come from the Tag field.
- `score_tags()` and `build_question()` require `templates`.
- `JevTagField` lives in `wagtail_jev.tag_field`; `wagtail_jev.models` still exports it.

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

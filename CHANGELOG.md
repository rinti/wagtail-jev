# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-09-19

### Added

- Tag suggestions for Wagtail pages via Jev (TypeSafe System One), one Noul question per candidate tag.
- `JevTaggableMixin` with per-field `jev_tag_fields` configuration (`JevTagField`): prompts, candidates, threshold and cap per tag field.
- `JevTagFieldPanel`: tag widget with a "Let Jev suggest tags" button that scores the editor's unsaved content.
- `jev_tag_pages` management command with `--field`, `--apply` and `--publish`.
- `WAGTAIL_JEV_*` settings, including customizable prompt templates.

[Unreleased]: https://github.com/rinti/wagtail-jev/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/rinti/wagtail-jev/releases/tag/v0.1.0

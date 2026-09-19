/**
 * Stimulus controller for the "Let Jev suggest tags" button rendered by
 * JevTagFieldPanel. Posts the page edit form's current data to the suggest
 * endpoint and adds the returned tags to the sibling tag widget.
 */
class JevSuggestController extends window.StimulusModule.Controller {
  static targets = ["button", "status"];
  static values = {
    url: String,
    model: String,
    field: String,
    messages: { type: Object, default: {} },
  };

  suggest() {
    const form = this.element.closest("form");
    const input = form && form.querySelector(`[name="${this.fieldValue}"]`);
    if (!form || !input) return;

    const data = new FormData(form);
    data.set("jev_model", this.modelValue);
    data.set("jev_field", this.fieldValue);
    const csrf = form.querySelector('input[name="csrfmiddlewaretoken"]');

    this.buttonTarget.disabled = true;
    this.statusTarget.textContent = this.messagesValue.loading || "";

    fetch(this.urlValue, {
      method: "POST",
      body: data,
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrf ? csrf.value : "",
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) =>
        response.json().then((json) => ({ ok: response.ok, json })),
      )
      .then(({ ok, json }) => {
        if (!ok) throw new Error(json.error || "Request failed");
        const tags = json.tags || [];
        if (!tags.length) {
          this.statusTarget.textContent = this.messagesValue.empty || "";
          return;
        }
        tags.forEach((tag) => this.addTag(input, tag.name));
        this.statusTarget.textContent =
          (this.messagesValue.added || "") +
          tags
            .map((tag) => `${tag.name} (${Math.round(tag.probability * 100)}%)`)
            .join(", ");
      })
      .catch((error) => {
        this.statusTarget.textContent =
          (this.messagesValue.error || "") + error.message;
      })
      .finally(() => {
        this.buttonTarget.disabled = false;
      });
  }

  addTag(input, name) {
    // Wagtail's w-tag controller wraps jQuery tag-it; use it so the chip renders.
    const $ = window.jQuery || window.$;
    if ($ && $(input).data("ui-tagit")) {
      $(input).tagit("createTag", name);
      return;
    }
    const current = input.value
      ? input.value.split(",").map((s) => s.trim()).filter(Boolean)
      : [];
    if (!current.includes(name)) current.push(name);
    input.value = current.join(", ");
  }
}

window.wagtail.app.register("jev-suggest", JevSuggestController);

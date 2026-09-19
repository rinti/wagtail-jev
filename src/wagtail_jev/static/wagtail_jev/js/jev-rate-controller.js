/**
 * Stimulus controller for the "Rate with Jev" button rendered by JevRatingPanel and
 * JevRatingFieldPanel. Posts the page edit form's current data to the rate endpoint,
 * naming a field when the button belongs to one, and shows one line per Rating: the
 * Quality's label, the most likely level and its percent, with every level's probability
 * behind a <details> element. Nothing is written to any form field.
 */
class JevRateController extends window.StimulusModule.Controller {
  static targets = ["button", "status", "ratings"];
  static values = {
    url: String,
    model: String,
    field: { type: String, default: "" },
    keys: { type: String, default: "" },
    messages: { type: Object, default: {} },
  };

  rate() {
    const form = this.element.closest("form");
    if (!form) return;

    const data = new FormData(form);
    data.set("jev_model", this.modelValue);
    if (this.fieldValue) data.set("jev_field", this.fieldValue);
    this.keysValue
      .split(",")
      .filter(Boolean)
      .forEach((key) => data.append("jev_keys", key));
    const csrf = form.querySelector('input[name="csrfmiddlewaretoken"]');

    this.buttonTarget.disabled = true;
    this.statusTarget.textContent = this.messagesValue.loading || "";
    this.ratingsTarget.replaceChildren();

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
        const ratings = json.ratings || [];
        if (!ratings.length) {
          this.statusTarget.textContent = this.messagesValue.empty || "";
          return;
        }
        this.statusTarget.textContent = "";
        ratings.forEach((rating) =>
          this.ratingsTarget.appendChild(this.renderRating(rating)),
        );
      })
      .catch((error) => {
        this.statusTarget.textContent =
          (this.messagesValue.error || "") + error.message;
      })
      .finally(() => {
        this.buttonTarget.disabled = false;
      });
  }

  renderRating(rating) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = `${rating.label}: ${rating.top_label} (${this.percent(rating.top_probability)})`;
    details.appendChild(summary);

    const list = document.createElement("ul");
    list.className = "w-ml-4";
    rating.levels.forEach((level) => {
      const item = document.createElement("li");
      item.textContent = `${level.label} ${this.percent(level.probability)}`;
      list.appendChild(item);
    });
    details.appendChild(list);
    return details;
  }

  percent(probability) {
    return `${Math.round(probability * 100)}%`;
  }
}

window.wagtail.app.register("jev-rate", JevRateController);

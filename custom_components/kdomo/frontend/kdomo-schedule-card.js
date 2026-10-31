/* K-Domo weekly editor v0.4.0. No credentials or cloud calls in the browser. */
const DAYS = [
  "Domenica",
  "Lunedì",
  "Martedì",
  "Mercoledì",
  "Giovedì",
  "Venerdì",
  "Sabato",
];
const ORDER = [1, 2, 3, 4, 5, 6, 0];
const copy = (value) => JSON.parse(JSON.stringify(value));
const time = (value) =>
  `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export function validateWeek(days, levels) {
  if (!Array.isArray(days) || days.length !== 7)
    throw new Error("Servono tutti e sette i giorni.");
  const seen = new Set();
  for (const day of days) {
    if (
      !Number.isInteger(day.day) ||
      day.day < 0 ||
      day.day > 6 ||
      seen.has(day.day)
    )
      throw new Error("Giorno non valido.");
    seen.add(day.day);
    if (!Array.isArray(day.slots) || !day.slots.length || day.slots.length > 8)
      throw new Error("Sono consentite da una a otto fasce al giorno.");
    let previous = 0;
    for (const slot of day.slots) {
      if (
        !levels.some((level) => level.id === slot.level) ||
        !Number.isInteger(slot.end) ||
        slot.end <= previous ||
        slot.end > 1440 ||
        slot.end === 1439
      )
        throw new Error("Orario o livello della fascia non valido.");
      previous = slot.end;
    }
    if (previous !== 1440)
      throw new Error("Ogni giorno deve arrivare a fine giornata.");
  }
}

export function splitSlot(slots, index) {
  if (slots.length >= 8) throw new Error("Il limite è otto fasce per giorno.");
  const begin = index ? slots[index - 1].end : 0;
  const end = slots[index].end;
  if (end - begin < 2) throw new Error("Fascia troppo breve da dividere.");
  const middle = begin + Math.floor((end - begin) / 2);
  if (middle === 1439) throw new Error("Fascia troppo breve da dividere.");
  slots.splice(index + 1, 0, { level: slots[index].level, end });
  slots[index].end = middle;
}

const STYLES = `
:host{display:block;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif)}
*{box-sizing:border-box}ha-card{display:block;background:var(--ha-card-background,var(--card-background-color));border-radius:var(--ha-card-border-radius,12px);border:1px solid var(--ha-card-border-color,var(--divider-color));padding:22px}
h2{font-size:20px;font-weight:400;margin:0 0 4px}.muted{font-size:12px;color:var(--secondary-text-color)}.header{display:flex;justify-content:space-between;gap:12px;align-items:start;margin-bottom:18px}.header>div{min-width:0;overflow-wrap:anywhere}
button,select,input{font:inherit;color:inherit}button{min-height:42px;padding:8px 12px;background:var(--ha-card-background,var(--card-background-color));border:1px solid var(--divider-color);border-radius:7px}button:disabled{opacity:.45}button:not(:disabled),select{cursor:pointer}button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
.axis-row,.day-row{display:grid;grid-template-columns:36px minmax(0,1fr);gap:8px;align-items:center}.axis{display:flex;justify-content:space-between;font-size:12px;color:var(--secondary-text-color);padding-bottom:7px;font-variant-numeric:tabular-nums}.day-row{margin-bottom:9px}.day-name{font-size:12px}.lane{display:flex;gap:1px;min-width:0;position:relative}.block{flex:none;min-width:0;position:relative;display:flex}
.segment{width:100%;min-width:0;min-height:46px;border:0;padding:0 2px;font-size:12px;border-radius:3px;overflow:hidden;background:var(--secondary-background-color);color:var(--primary-text-color)}.segment[data-tone="1"]{background:color-mix(in srgb,var(--primary-text-color) 14%,var(--card-background-color))}.segment[data-tone="2"]{background:repeating-linear-gradient(135deg,var(--secondary-background-color),var(--secondary-background-color) 6px,color-mix(in srgb,var(--primary-text-color) 16%,var(--card-background-color)) 6px,color-mix(in srgb,var(--primary-text-color) 16%,var(--card-background-color)) 7px)}.segment[data-tone="3"]{background:color-mix(in srgb,var(--primary-text-color) 26%,var(--card-background-color))}.segment[aria-pressed="true"]{background:var(--primary-text-color);color:var(--card-background-color)}
.handle{position:absolute;right:-6px;top:0;height:46px;min-height:46px;width:13px;padding:0;border:0;background:transparent;border-radius:0;touch-action:none;cursor:ew-resize;z-index:2}.handle:after{content:"";position:absolute;width:3px;height:24px;top:11px;left:5px;background:var(--card-background-color);box-shadow:0 0 0 1px var(--primary-text-color);border-radius:2px}
.legend{display:flex;gap:6px 15px;flex-wrap:wrap;margin:16px 0 20px;font-size:12px;color:var(--secondary-text-color)}.editor{border-top:1px solid var(--divider-color);padding-top:16px}.selected{font-variant-numeric:tabular-nums;margin-bottom:12px}.fields,.actions,.footer{display:flex;flex-wrap:wrap;gap:10px;align-items:end}label{display:block;font-size:12px;color:var(--secondary-text-color)}select,input[type="time"]{display:block;width:100%;margin-top:4px;min-height:42px;padding:8px;background:var(--ha-card-background,var(--card-background-color));color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:6px;font-size:14px}.level-field{flex:1;min-width:160px}.end-field{width:125px}.range-label{margin-top:14px}input[type="range"]{display:block;width:100%;margin:8px 0;min-height:32px;accent-color:var(--primary-color)}.actions{margin-top:12px}.footer{margin-top:20px;justify-content:space-between;align-items:center}.save{background:var(--primary-text-color);color:var(--card-background-color);border-color:var(--primary-text-color)}.message{margin-top:12px;font-size:12px;overflow-wrap:anywhere}.error{color:var(--error-color)}.review{margin-top:16px;padding-top:14px;border-top:1px solid var(--divider-color)}.review-row{margin:8px 0;overflow-wrap:anywhere}.review-row small{display:block;color:var(--secondary-text-color)}.long{display:none}.warning{margin:12px 0;font-size:12px}
@media(min-width:650px){.long{display:inline}.short{display:none}}@media(max-width:420px){ha-card{padding:14px}.axis-row,.day-row{grid-template-columns:30px minmax(0,1fr);gap:5px}.quarter{visibility:hidden}select,input[type="time"]{font-size:16px}.header button{padding:8px}}
@media(pointer:coarse){.handle{display:none}}
`;

export class KdomoScheduleCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._day = 1;
    this._slot = 0;
    this._requestId = 0;
    this._busy = false;
    this._message = "";
    this._error = false;
  }
  setConfig(config) {
    if (!config.entity || !config.entity.startsWith("climate."))
      throw new Error("Seleziona un’entità climate K-Domo.");
    this._config = { ...config };
    this._schedule = null;
    this._draft = null;
    this._requestId++;
    this._busy = false;
    this._review = false;
    this._stale = false;
    this._reloadReview = false;
    this._loadFailed = false;
    this._render();
    if (this._hass && this.isConnected) this._load();
  }
  set hass(hass) {
    this._hass = hass;
    const state = this._config && hass.states[this._config.entity];
    const revision = state?.attributes.kdomo_schedule_revision;
    const offline = !state || ["unavailable", "unknown"].includes(state.state);
    if (this._schedule)
      this._schedule.write_enabled =
        !!state?.attributes.kdomo_schedule_write_enabled;
    if (this._schedule && revision && revision !== this._schedule.revision) {
      if (this._dirty()) {
        this._stale = true;
        this._review = false;
        this._render();
      } else if (!this._busy && this.isConnected) this._load();
    } else if (
      !this._schedule &&
      !this._busy &&
      this.isConnected &&
      state &&
      !this._loadFailed
    )
      this._load();
    else if (
      this._schedule &&
      (this._canWrite !==
        (!!state?.attributes.kdomo_schedule_write_enabled && !offline) ||
        this._stateAtRender !== state?.state)
    )
      this._render();
  }
  connectedCallback() {
    if (this._hass && this._config && !this._schedule) this._load();
  }
  disconnectedCallback() {
    this._requestId++;
    this._busy = false;
  }
  getCardSize() {
    return 12;
  }
  getGridOptions() {
    return { columns: 12, rows: "auto", min_columns: 6 };
  }
  static getConfigElement() {
    return document.createElement("kdomo-schedule-card-editor");
  }
  static getStubConfig(hass) {
    return {
      entity:
        Object.keys(hass.states).find(
          (id) =>
            id.startsWith("climate.") &&
            "kdomo_program" in hass.states[id].attributes,
        ) || "climate.studio",
    };
  }
  _dirty() {
    return !!this._schedule && !same(this._draft, this._schedule.days);
  }
  async _call(service, data) {
    const result = await this._hass.callWS({
      type: "call_service",
      domain: "kdomo",
      service,
      service_data: { entity_id: this._config.entity, ...data },
      return_response: true,
    });
    if (!result?.response?.days || !Array.isArray(result.response.levels))
      throw new Error("Risposta della pianificazione non valida.");
    validateWeek(result.response.days, result.response.levels);
    return result.response;
  }
  async _load() {
    if (this._busy || !this._hass || !this._config) return;
    const id = ++this._requestId;
    this._busy = true;
    this._loadFailed = false;
    this._message = "Lettura della settimana…";
    this._error = false;
    this._render();
    try {
      const data = await this._call("get_schedule", {});
      if (id !== this._requestId) return;
      this._schedule = data;
      this._draft = copy(data.days);
      this._stale = false;
      this._review = false;
      this._day = 1;
      this._slot = 0;
      this._message = "";
    } catch (error) {
      if (id === this._requestId) {
        this._loadFailed = true;
        this._message = error.message || "Lettura non riuscita.";
        this._error = true;
      }
    } finally {
      if (id === this._requestId) {
        this._busy = false;
        this._render();
      }
    }
  }
  async _save() {
    if (!this._review || !this._canWrite || this._stale || this._busy) return;
    const id = ++this._requestId;
    this._busy = true;
    this._message = "Invio e verifica della settimana…";
    this._error = false;
    this._render();
    try {
      const data = await this._call("set_schedule", {
        revision: this._schedule.revision,
        days: this._draft,
      });
      if (id !== this._requestId) return;
      this._schedule = data;
      this._draft = copy(data.days);
      this._review = false;
      this._stale = false;
      this._message = "Settimana confermata dal cloud K-Domo.";
    } catch (error) {
      if (id === this._requestId) {
        this._message =
          (error.message || "Conferma non riuscita.") +
          " Nessun reinvio automatico. Controlla K-Domo e ricarica prima di riprovare.";
        this._error = true;
        this._review = false;
        this._stale = true;
      }
    } finally {
      if (id === this._requestId) {
        this._busy = false;
        this._render();
      }
    }
  }
  _text(tag, text, className) {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    return el;
  }
  _button(text, action, disabled = false, className = "") {
    const b = this._text("button", text, className);
    b.type = "button";
    b.disabled = disabled;
    b.onclick = action;
    return b;
  }
  _slots(day = this._day) {
    return this._draft.find((d) => d.day === day).slots;
  }
  _level(id) {
    return this._schedule.levels.find((l) => l.id === id);
  }
  _temperature(level) {
    if (level.temperature == null) return "";
    const nativeUnit =
      this._schedule.scale === 1
        ? "°F"
        : this._schedule.scale === 0
          ? "°C"
          : null;
    if (!nativeUnit) return "";
    const unit = this._hass.config?.unit_system?.temperature || nativeUnit;
    let n = level.temperature;
    if (unit !== nativeUnit)
      n = unit === "°F" ? (n * 9) / 5 + 32 : ((n - 32) * 5) / 9;
    return ` · ${new Intl.NumberFormat(this._hass.locale?.language || "it", { maximumFractionDigits: 1 }).format(n)} ${unit}`;
  }
  _edited() {
    this._review = false;
    this._message = "Bozza modificata · Nessun comando inviato";
    this._error = false;
    this._render();
  }
  _end(value) {
    const slots = this._slots();
    const begin = this._slot ? slots[this._slot - 1].end : 0;
    const next = slots[this._slot + 1];
    if (
      !next ||
      !Number.isInteger(value) ||
      value <= begin ||
      value >= next.end ||
      value === 1439
    )
      return;
    slots[this._slot].end = value;
    this._edited();
  }
  _render() {
    if (!this.shadowRoot || !this._config) return;
    const state = this._hass?.states[this._config.entity];
    this._stateAtRender = state?.state;
    this._offline = !state || ["unavailable", "unknown"].includes(state.state);
    this._canWrite =
      !!this._schedule?.write_enabled &&
      !!state?.attributes.kdomo_schedule_write_enabled &&
      !this._offline;
    this.shadowRoot.innerHTML = `<style>${STYLES}</style><ha-card><div class="header"><div><h2></h2><div class="muted" id="subtitle"></div></div><button type="button" id="reload">Ricarica</button></div><div id="content"></div><div id="message" class="message" role="status" aria-live="polite"></div></ha-card>`;
    const q = (id) => this.shadowRoot.getElementById(id);
    this.shadowRoot.querySelector("h2").textContent =
      this._config.title ||
      `Programmazione ${state?.attributes.friendly_name || this._config.entity}`;
    q("reload").disabled = this._busy;
    q("reload").onclick = () => {
      if (this._dirty()) {
        this._review = false;
        this._reloadReview = true;
        this._render();
      } else this._load();
    };
    q("message").textContent = this._message;
    q("message").classList.toggle("error", this._error);
    if (!this._schedule) {
      q("subtitle").textContent = "Giacomini K-Domo · Programma corrente";
      return;
    }
    q("subtitle").textContent =
      `${this._schedule.name} · ${this._schedule.season === "heat" ? "Riscaldamento" : "Raffrescamento"} · Orari locali del termostato`;
    const content = q("content");
    this._lanes = new Map();
    if (this._reloadReview) {
      const ask = this._text(
        "div",
        "Scartare la bozza e rileggere il programma dal cloud?",
        "warning",
      );
      const actions = this._text("div", "", "actions");
      actions.append(
        this._button("Scarta e ricarica", () => {
          this._reloadReview = false;
          this._load();
        }),
        this._button("Conserva la bozza", () => {
          this._reloadReview = false;
          this._render();
        }),
      );
      content.append(ask, actions);
      return;
    }
    if (this._stale)
      content.append(
        this._text(
          "div",
          "Il programma è cambiato o l’ultimo invio è incerto. Ricarica prima di salvare.",
          "warning",
        ),
      );
    if (!this._canWrite)
      content.append(
        this._text(
          "div",
          this._offline
            ? "Termostato non disponibile. Ultima settimana letta; scritture bloccate."
            : "Sola lettura. Per modificare, abilita controlli e modifica pianificazioni nelle opzioni K-Domo.",
          "warning",
        ),
      );
    const axis = this._text("div", "", "axis-row");
    axis.append(this._text("span", ""));
    const ticks = this._text("div", "", "axis");
    [0, 3, 6, 9, 12, 15, 18, 21, 24].forEach((h, i) =>
      ticks.append(
        this._text("span", String(h).padStart(2, "0"), i % 2 ? "quarter" : ""),
      ),
    );
    axis.append(ticks);
    content.append(axis);
    const editingDisabled =
      !this._canWrite || this._busy || this._stale || this._review;
    for (const day of ORDER) {
      const row = this._text("div", "", "day-row");
      row.append(this._text("span", DAYS[day].slice(0, 3), "day-name"));
      const lane = this._text("div", "", "lane");
      this._lanes.set(day, lane);
      const slots = this._slots(day);
      slots.forEach((slot, i) => {
        const start = i ? slots[i - 1].end : 0,
          duration = slot.end - start,
          level = this._level(slot.level);
        const block = this._text("div", "", "block");
        block.style.width = `calc(${(duration / 1440) * 100}% - ${(slots.length - 1) / slots.length}px)`;
        const b = this._button(
          "",
          () => {
            this._day = day;
            this._slot = i;
            this._review = false;
            this._render();
          },
          this._busy,
          "segment",
        );
        b.dataset.level = slot.level;
        b.dataset.tone =
          level.name === "Notte"
            ? "2"
            : level.name === "Comfort+"
              ? "3"
              : level.name.startsWith("Economy")
                ? "1"
                : "0";
        b.setAttribute(
          "aria-pressed",
          String(day === this._day && i === this._slot),
        );
        b.setAttribute(
          "aria-label",
          `${DAYS[day]}, ${time(start)}–${time(slot.end)}, ${level.name}${this._temperature(level)}`,
        );
        if (duration >= 90) {
          b.append(
            this._text(
              "span",
              level.name === "Comfort+"
                ? "C+"
                : level.name === "Economy+"
                  ? "E+"
                  : level.name[0],
              "short",
            ),
            this._text(
              "span",
              duration >= 210
                ? level.name
                : level.name === "Comfort+"
                  ? "C+"
                  : level.name[0],
              "long",
            ),
          );
        }
        block.append(b);
        if (
          day === this._day &&
          i === this._slot &&
          i < slots.length - 1 &&
          !editingDisabled
        ) {
          const handle = this._button("", () => {}, false, "handle");
          handle.setAttribute(
            "aria-label",
            "Trascina il confine, oppure usa l’orario sotto",
          );
          handle.onpointerdown = (e) => {
            e.preventDefault();
            const bounds = lane.getBoundingClientRect();
            handle.setPointerCapture(e.pointerId);
            handle.onpointermove = (ev) => {
              const value = Math.max(
                start + 1,
                Math.min(
                  slots[i + 1].end - 1,
                  Math.round(
                    (((ev.clientX - bounds.left) / bounds.width) * 1440) / 15,
                  ) * 15,
                ),
              );
              if (value === 1439) return;
              slot.end = value;
              [...lane.children].forEach(
                (el, j) =>
                  (el.style.width = `calc(${((slots[j].end - (j ? slots[j - 1].end : 0)) / 1440) * 100}% - ${(slots.length - 1) / slots.length}px)`),
              );
              q("selected").textContent =
                `${DAYS[day]} · ${time(start)}–${time(value)} · ${level.name}`;
              q("end").value = time(value);
              q("range").value = value;
            };
            const done = () => {
              handle.onpointermove = null;
              this._edited();
            };
            handle.onpointerup = done;
            handle.onpointercancel = done;
          };
          block.append(handle);
        }
        lane.append(block);
      });
      row.append(lane);
      content.append(row);
    }
    const legend = this._text("div", "", "legend");
    this._schedule.levels.forEach((l) =>
      legend.append(this._text("span", l.name + this._temperature(l))),
    );
    content.append(legend);
    const slots = this._slots();
    this._slot = Math.min(this._slot, slots.length - 1);
    const slot = slots[this._slot],
      begin = this._slot ? slots[this._slot - 1].end : 0,
      last = this._slot === slots.length - 1;
    const editor = this._text("section", "", "editor");
    const selected = this._text(
      "div",
      `${DAYS[this._day]} · ${time(begin)}–${time(slot.end)} · ${this._level(slot.level).name}`,
      "selected",
    );
    selected.id = "selected";
    editor.append(selected);
    const slotLabel = this._text(
      "label",
      "Seleziona fascia (anche da tastiera)",
    );
    const slotPicker = document.createElement("select");
    slotPicker.setAttribute(
      "aria-label",
      "Seleziona una fascia della settimana",
    );
    slotPicker.disabled = this._busy;
    for (const d of ORDER) {
      const group = document.createElement("optgroup");
      group.label = DAYS[d];
      this._slots(d).forEach((s, i) => {
        const option = this._text(
          "option",
          `${time(i ? this._slots(d)[i - 1].end : 0)}–${time(s.end)} · ${this._level(s.level).name}`,
        );
        option.value = `${d}:${i}`;
        group.append(option);
      });
      slotPicker.append(group);
    }
    slotPicker.value = `${this._day}:${this._slot}`;
    slotPicker.onchange = () => {
      [this._day, this._slot] = slotPicker.value.split(":").map(Number);
      this._review = false;
      this._render();
    };
    slotLabel.append(slotPicker);
    editor.append(slotLabel);

    const fields = this._text("div", "", "fields"),
      label = this._text("label", "Livello della fascia", "level-field"),
      select = document.createElement("select");
    select.disabled = editingDisabled;
    this._schedule.levels.forEach((l) => {
      const o = this._text("option", l.name + this._temperature(l));
      o.value = l.id;
      select.append(o);
    });
    select.value = slot.level;
    select.onchange = () => {
      slot.level = Number(select.value);
      this._edited();
    };
    label.append(select);
    fields.append(label);
    const endLabel = this._text("label", "Fine fascia", "end-field"),
      end = document.createElement("input");
    end.type = "time";
    end.id = "end";
    end.step = 60;
    end.value = time(last ? 1439 : slot.end);
    end.disabled = last || editingDisabled;
    end.onchange = () => {
      const [h, m] = end.value.split(":").map(Number);
      this._end(h * 60 + m);
    };
    endLabel.append(end);
    fields.append(endLabel);
    editor.append(fields);
    const rangeLabel = this._text(
        "label",
        "Sposta il confine della fascia",
        "range-label",
      ),
      range = document.createElement("input");
    range.id = "range";
    range.type = "range";
    range.min = begin + 1;
    range.max = last ? 1440 : slots[this._slot + 1].end - 1;
    range.step = 1;
    range.value = slot.end;
    range.disabled = last || editingDisabled;
    range.setAttribute("aria-valuetext", time(slot.end));
    range.oninput = () => {
      const value = Number(range.value);
      if (value === 1439) return;
      slot.end = value;
      this._review = false;
      const lane = this._lanes.get(this._day);
      [...lane.children].forEach(
        (el, j) =>
          (el.style.width = `calc(${((slots[j].end - (j ? slots[j - 1].end : 0)) / 1440) * 100}% - ${(slots.length - 1) / slots.length}px)`),
      );
      selected.textContent = `${DAYS[this._day]} · ${time(begin)}–${time(value)} · ${this._level(slot.level).name}`;
      end.value = time(value);
      range.setAttribute("aria-valuetext", time(value));
    };
    range.onchange = () => this._edited();
    rangeLabel.append(range);
    editor.append(rangeLabel);
    const actions = this._text("div", "", "actions");
    actions.append(
      this._button(
        "Dividi fascia",
        () => {
          try {
            splitSlot(slots, this._slot);
            this._slot++;
            this._edited();
          } catch (error) {
            this._message = error.message;
            this._error = true;
            this._render();
          }
        },
        editingDisabled || slots.length >= 8 || slot.end - begin < 2,
      ),
      this._button(
        "Unisci alla successiva",
        () => {
          slot.end = slots[this._slot + 1].end;
          slots.splice(this._slot + 1, 1);
          this._edited();
        },
        editingDisabled || last,
      ),
    );
    const copySelect = document.createElement("select");
    copySelect.setAttribute("aria-label", "Giorni su cui copiare la giornata");
    for (const [value, text] of [
      ["work", "Lunedì–venerdì"],
      ["weekend", "Sabato e domenica"],
      ["all", "Tutta la settimana"],
    ]) {
      const o = this._text("option", text);
      o.value = value;
      copySelect.append(o);
    }
    copySelect.disabled = editingDisabled;
    actions.append(
      copySelect,
      this._button(
        "Copia giornata",
        () => {
          const targets =
            copySelect.value === "work"
              ? [1, 2, 3, 4, 5]
              : copySelect.value === "weekend"
                ? [6, 0]
                : [0, 1, 2, 3, 4, 5, 6];
          const source = copy(slots);
          targets.forEach(
            (d) => (this._draft.find((x) => x.day === d).slots = copy(source)),
          );
          this._edited();
        },
        editingDisabled,
      ),
    );
    editor.append(actions);
    content.append(editor);
    const changed = ORDER.filter(
      (d) =>
        !same(
          this._slots(d),
          this._schedule.days.find((x) => x.day === d).slots,
        ),
    );
    if (this._review) {
      const review = this._text("div", "", "review");
      review.append(
        this._text(
          "div",
          `Inviare la settimana completa a K-Domo? Giorni modificati: ${changed.map((d) => DAYS[d]).join(", ")}.`,
        ),
      );
      for (const d of changed) {
        const summary = (items) =>
          items
            .map((s) => `${time(s.end)} ${this._level(s.level).name}`)
            .join(" · ");
        const line = this._text("div", DAYS[d], "review-row");
        line.append(
          this._text(
            "small",
            "Prima: " +
              summary(this._schedule.days.find((x) => x.day === d).slots),
          ),
          this._text("small", "Dopo: " + summary(this._slots(d))),
        );
        review.append(line);
      }
      const a = this._text("div", "", "actions");
      a.append(
        this._button("Conferma invio", () => this._save(), this._busy, "save"),
        this._button(
          "Torna alla bozza",
          () => {
            this._review = false;
            this._render();
          },
          this._busy,
        ),
      );
      review.append(a);
      content.append(review);
    }
    const footer = this._text("div", "", "footer");
    footer.append(
      this._text(
        "span",
        changed.length
          ? `${changed.length} giorni modificati nella bozza`
          : "Nessuna modifica",
        "muted",
      ),
      this._button(
        "Salva settimana",
        () => {
          try {
            validateWeek(this._draft, this._schedule.levels);
            this._review = true;
            this._render();
          } catch (error) {
            this._message = error.message;
            this._error = true;
            this._render();
          }
        },
        editingDisabled || !changed.length,
        "save",
      ),
    );
    content.append(footer);
  }
}

class KdomoScheduleCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }
  set hass(hass) {
    this._hass = hass;
    this._render();
  }
  _render() {
    if (!this._config || !this._hass) return;
    this.shadowRoot.innerHTML =
      "<label>Termostato K-Domo <select></select></label>";
    const select = this.shadowRoot.querySelector("select");
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "Seleziona un termostato";
    select.append(blank);
    for (const [id, state] of Object.entries(this._hass.states)) {
      if (!id.startsWith("climate.") || !("kdomo_program" in state.attributes))
        continue;
      const option = document.createElement("option");
      option.value = id;
      option.textContent = state.attributes.friendly_name || id;
      select.append(option);
    }
    select.value = this._config.entity || "";
    select.onchange = () => {
      this._config = { ...this._config, entity: select.value };
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          detail: { config: this._config },
          bubbles: true,
          composed: true,
        }),
      );
    };
  }
}
if (!customElements.get("kdomo-schedule-card"))
  customElements.define("kdomo-schedule-card", KdomoScheduleCard);
if (!customElements.get("kdomo-schedule-card-editor"))
  customElements.define("kdomo-schedule-card-editor", KdomoScheduleCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "kdomo-schedule-card"))
  window.customCards.push({
    type: "kdomo-schedule-card",
    name: "K-Domo · Programmazione",
    description: "Editor della settimana del programma corrente",
    preview: false,
  });

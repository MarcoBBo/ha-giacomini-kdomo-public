import assert from "node:assert/strict";
import { test } from "node:test";
import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body></body></html>", {
  url: "http://ha.invalid/",
});
for (const name of [
  "window",
  "document",
  "HTMLElement",
  "customElements",
  "CustomEvent",
])
  globalThis[name] = dom.window[name];
const { KdomoScheduleCard, KdomoThermostatsCard, validateWeek, splitSlot } =
  await import("../../custom_components/kdomo/frontend/kdomo-schedule-card.js");
const clone = (value) => JSON.parse(JSON.stringify(value));
const base = () => ({
  program: 0,
  name: "Inverno",
  season: "heat",
  revision: "a".repeat(64),
  scale: 0,
  write_enabled: true,
  mode: 1,
  status: 0,
  days: Array.from({ length: 7 }, (_, day) => ({
    day,
    slots: [
      { level: 2, end: 390 },
      { level: 1, end: 540 },
      { level: 3, end: 1080 },
      { level: 4, end: 1380 },
      { level: 2, end: 1440 },
    ],
  })),
  levels: [
    { id: 0, name: "Antigelo", temperature: 7 },
    { id: 1, name: "Comfort", temperature: 21 },
    { id: 2, name: "Notte", temperature: 18 },
    { id: 3, name: "Economy", temperature: 17 },
    { id: 4, name: "Comfort+", temperature: 22 },
    { id: 5, name: "Economy+", temperature: 16 },
    { id: 6, name: "Stop", temperature: null },
  ],
});
const tick = () => new Promise((resolve) => setImmediate(resolve));
async function fixture({ enabled = true, failSave = false } = {}) {
  const calls = [];
  let current = base();
  current.write_enabled = enabled;
  const hass = {
    states: {
      "climate.studio": {
        attributes: {
          friendly_name: "Studio",
          kdomo_program: 0,
          kdomo_schedule_revision: current.revision,
          kdomo_schedule_write_enabled: enabled,
        },
      },
    },
    locale: { language: "it" },
    config: { unit_system: { temperature: "°C" } },
    callWS: async (request) => {
      calls.push(clone(request));
      if (request.service === "set_schedule") {
        if (failSave) throw new Error("Conferma non riuscita");
        current = {
          ...current,
          days: clone(request.service_data.days),
          revision: "b".repeat(64),
        };
        hass.states["climate.studio"].attributes.kdomo_schedule_revision =
          current.revision;
      }
      return { response: clone(current) };
    },
  };
  const card = new KdomoScheduleCard();
  card.setConfig({ entity: "climate.studio" });
  card.hass = hass;
  document.body.append(card);
  await tick();
  return {
    card,
    hass,
    calls,
    root: card.shadowRoot,
    dispose: () => card.remove(),
  };
}
function button(root, label) {
  return [...root.querySelectorAll("button")].find(
    (b) => b.textContent === label,
  );
}
function choose(root, level) {
  const select = root.querySelector(".level-field select");
  select.value = String(level);
  select.dispatchEvent(new dom.window.Event("change"));
}

test("renders the real cloud week and never writes during load or selection", async () => {
  const f = await fixture();
  assert.equal(f.root.querySelectorAll(".day-row").length, 7);
  assert.equal(f.root.querySelectorAll(".segment").length, 35);
  f.root.querySelectorAll(".segment")[1].click();
  assert.match(f.root.getElementById("selected").textContent, /06:30–09:00/);
  assert.equal(f.calls.length, 1);
  assert.equal(f.calls[0].service, "get_schedule");
  assert.equal(f.calls[0].service_data.entity_id, "climate.studio");
  assert.equal(f.calls[0].return_response, true);
  assert.equal(
    window.customCards.filter((c) => c.type === "kdomo-schedule-card").length,
    1,
  );
  f.dispose();
});

test("draft editing, split, merge and copy produce no POST-equivalent action until confirmation", async () => {
  const f = await fixture();
  f.root.querySelectorAll(".segment")[1].click();
  choose(f.root, 4);
  assert.equal(f.card._draft.find((d) => d.day === 1).slots[1].level, 4);
  button(f.root, "Dividi fascia").click();
  assert.equal(f.card._draft.find((d) => d.day === 1).slots.length, 6);
  button(f.root, "Unisci alla successiva").click();
  assert.equal(f.card._draft.find((d) => d.day === 1).slots.length, 5);
  button(f.root, "Copia giornata").click();
  for (const d of [1, 2, 3, 4, 5])
    assert.deepEqual(f.card._slots(d), f.card._slots(1));
  assert.equal(f.calls.length, 1);
  button(f.root, "Salva settimana").click();
  assert.match(
    f.root.querySelector(".review").textContent,
    /Giorni modificati/,
  );
  assert.equal(f.calls.length, 1);
  button(f.root, "Conferma invio").click();
  await tick();
  assert.equal(f.calls.length, 2);
  const write = f.calls[1];
  assert.equal(write.service, "set_schedule");
  assert.equal(write.service_data.revision, "a".repeat(64));
  assert.equal(write.service_data.days.length, 7);
  assert.match(f.root.getElementById("message").textContent, /confermata/);
  assert.equal(f.card._dirty(), false);
  f.dispose();
});

test("range updates the lanes live and keeps its DOM element while dragging", async () => {
  const f = await fixture();
  f.root.querySelectorAll(".segment")[1].click();
  const range = f.root.getElementById("range");
  range.value = "570";
  range.dispatchEvent(new dom.window.Event("input"));
  assert.equal(f.root.getElementById("range"), range);
  assert.match(f.root.getElementById("selected").textContent, /09:30/);
  assert.equal(f.card._slots()[1].end, 570);
  range.dispatchEvent(new dom.window.Event("change"));
  assert.equal(f.card._dirty(), true);
  assert.equal(f.calls.length, 1);
  f.dispose();
});

test("read-only options prevent editing and saving", async () => {
  const f = await fixture({ enabled: false });
  assert.equal(f.root.querySelector(".level-field select").disabled, true);
  assert.equal(button(f.root, "Salva settimana").disabled, true);
  assert.equal(button(f.root, "Dividi fascia").disabled, true);
  assert.equal(f.calls.length, 1);
  f.dispose();
});

test("external revision change never overwrites a draft and blocks save", async () => {
  const f = await fixture();
  choose(f.root, 1);
  const draft = clone(f.card._draft);
  f.hass.states["climate.studio"].attributes.kdomo_schedule_revision =
    "c".repeat(64);
  f.card.hass = f.hass;
  assert.equal(f.card._stale, true);
  assert.deepEqual(f.card._draft, draft);
  assert.equal(button(f.root, "Salva settimana").disabled, true);
  assert.equal(f.calls.length, 1);
  f.root.getElementById("reload").click();
  assert.ok(button(f.root, "Scarta e ricarica"));
  button(f.root, "Conserva la bozza").click();
  assert.deepEqual(f.card._draft, draft);
  f.dispose();
});

test("uncertain save is not retried, draft is retained and reload is required", async () => {
  const f = await fixture({ failSave: true });
  choose(f.root, 1);
  button(f.root, "Salva settimana").click();
  button(f.root, "Conferma invio").click();
  await tick();
  assert.equal(f.calls.filter((c) => c.service === "set_schedule").length, 1);
  assert.equal(f.card._dirty(), true);
  assert.equal(button(f.root, "Salva settimana").disabled, true);
  assert.match(
    f.root.getElementById("message").textContent,
    /Nessun reinvio automatico/,
  );
  f.dispose();
});

test("cloud-provided names are text, not executable HTML", async () => {
  const f = await fixture();
  f.card._schedule.name = "<img src=x onerror=alert(1)>";
  f.card._schedule.levels[1].name = "<script>bad()</script>";
  f.card._render();
  assert.equal(f.root.querySelectorAll("img,script").length, 0);
  assert.match(f.root.getElementById("subtitle").textContent, /<img/);
  f.dispose();
});

test("week validation refuses partial, overlapping and wrong-season slots", () => {
  const week = base();
  assert.doesNotThrow(() => validateWeek(week.days, week.levels));
  for (const mutate of [
    (d) => d.pop(),
    (d) => (d[1].day = 0),
    (d) => (d[0].slots[1].end = 20),
    (d) => (d[0].slots[0].level = 9),
    (d) => (d[0].slots.at(-1).end = 1439),
  ]) {
    const days = clone(week.days);
    mutate(days);
    assert.throws(() => validateWeek(days, week.levels));
  }
  const slots = [{ level: 1, end: 1440 }];
  splitSlot(slots, 0);
  assert.deepEqual(slots, [
    { level: 1, end: 720 },
    { level: 1, end: 1440 },
  ]);
  assert.throws(() =>
    splitSlot(
      Array.from({ length: 8 }, () => ({ level: 1, end: 1440 })),
      0,
    ),
  );
});

test("Fahrenheit values are displayed using HA preferred Celsius", async () => {
  const f = await fixture();
  f.card._schedule.scale = 1;
  f.card._schedule.levels[1].temperature = 71.6;
  f.card._render();
  assert.match(f.root.querySelector(".legend").textContent, /22 °C/);
  f.dispose();
});

test("card editor selects existing K-Domo entities and emits configuration", async () => {
  const f = await fixture();
  const editor = KdomoScheduleCard.getConfigElement();
  editor.setConfig({ entity: "climate.studio" });
  editor.hass = f.hass;
  const select = editor.shadowRoot.querySelector("select");
  assert.equal(select.options.length, 2);
  let changed;
  editor.addEventListener(
    "config-changed",
    (event) => (changed = event.detail.config),
  );
  select.value = "climate.studio";
  select.dispatchEvent(new dom.window.Event("change"));
  assert.equal(changed.entity, "climate.studio");
  f.dispose();
});

test("options changes and offline state update controls without losing a draft", async () => {
  const f = await fixture({ enabled: false });
  f.hass.states["climate.studio"].attributes.kdomo_schedule_write_enabled =
    true;
  f.card.hass = f.hass;
  assert.equal(f.root.querySelector(".level-field select").disabled, false);
  choose(f.root, 1);
  const draft = clone(f.card._draft);
  f.hass.states["climate.studio"].state = "unavailable";
  f.card.hass = f.hass;
  assert.equal(button(f.root, "Salva settimana").disabled, true);
  assert.deepEqual(f.card._draft, draft);
  f.hass.states["climate.studio"].state = "off";
  f.card.hass = f.hass;
  assert.equal(button(f.root, "Salva settimana").disabled, false);
  assert.equal(f.calls.length, 1);
  f.dispose();
});

test("pointer drag changes a boundary and stays inside adjacent slots", async () => {
  const f = await fixture();
  f.root.querySelectorAll(".segment")[1].click();
  const handle = f.root.querySelector(".handle");
  const lane = handle.parentElement.parentElement;
  lane.getBoundingClientRect = () => ({ left: 0, width: 720 });
  handle.setPointerCapture = () => {};
  handle.onpointerdown({ preventDefault() {}, pointerId: 1 });
  handle.onpointermove({ clientX: 300 });
  assert.equal(f.card._slots()[1].end, 600);
  assert.match(f.root.getElementById("selected").textContent, /10:00/);
  handle.onpointerup();
  assert.equal(f.card._dirty(), true);
  assert.equal(f.calls.length, 1);
  f.dispose();
});

test("split never creates the reserved 23:59 boundary", () => {
  const slots = [
    { level: 1, end: 1438 },
    { level: 2, end: 1440 },
  ];
  assert.throws(() => splitSlot(slots, 1));
  assert.equal(slots.length, 2);
});

test("accessible slot picker reaches every day and tiny intervals", async () => {
  const f = await fixture();
  const picker = f.root.querySelector(
    '[aria-label="Seleziona una fascia della settimana"]',
  );
  assert.equal(picker.options.length, 35);
  picker.value = "0:4";
  picker.dispatchEvent(new dom.window.Event("change"));
  assert.match(
    f.root.getElementById("selected").textContent,
    /Domenica · 23:00–24:00/,
  );
  assert.equal(f.calls.length, 1);
  f.dispose();
});

test("compact thermostat panel shows only the selected device's temperatures and opens native controls", async () => {
  const f = await fixture();
  f.calls.length = 0;
  const original = f.hass.callWS;
  f.hass.states["climate.studio"].state = "auto";
  f.hass.states["climate.studio"].attributes.current_temperature = 20.5;
  f.hass.states["number.studio_comfort"] = {
    state: "21",
    attributes: { unit_of_measurement: "°C" },
  };
  f.hass.states["number.other_comfort"] = {
    state: "30",
    attributes: { unit_of_measurement: "°C" },
  };
  f.hass.callWS = async (request) =>
    request.type === "config/entity_registry/list"
      ? [
          {
            entity_id: "climate.studio",
            platform: "kdomo",
            device_id: "studio",
            unique_id: "plant:one:climate",
          },
          {
            entity_id: "number.studio_comfort",
            platform: "kdomo",
            device_id: "studio",
            unique_id: "plant:one:heatingtempcomfort",
          },
          {
            entity_id: "number.other_comfort",
            platform: "kdomo",
            device_id: "other",
            unique_id: "plant:two:heatingtempcomfort",
          },
        ]
      : original(request);
  const card = new KdomoThermostatsCard();
  card.setConfig({ entities: ["climate.studio"] });
  card.hass = f.hass;
  document.body.append(card);
  card.shadowRoot.querySelector(".room").click();
  await tick();
  assert.match(card.shadowRoot.querySelector("dialog").textContent, /20.5/);
  [...card.shadowRoot.querySelectorAll(".tab")]
    .find((x) => x.textContent === "Temperature")
    .click();
  assert.match(card.shadowRoot.querySelector(".panel").textContent, /21 °C/);
  assert.doesNotMatch(
    card.shadowRoot.querySelector(".panel").textContent,
    /30 °C/,
  );
  let opened;
  card.addEventListener("hass-more-info", (event) => {
    opened = event.detail.entityId;
  });
  card.shadowRoot.querySelector(".preset").click();
  assert.equal(opened, "number.studio_comfort");
  assert.equal(f.calls.length, 0);
  card.remove();
  f.dispose();
});

test("compact list displays humidity and distinct modes, including unavailable readings", async () => {
  const f = await fixture();
  const card = new KdomoThermostatsCard();
  const state = f.hass.states["climate.studio"];
  state.attributes.current_temperature = 20.5;
  state.attributes.current_humidity = 0;
  card.setConfig({ entities: ["climate.studio"] });
  for (const [mode, css, label] of [
    ["auto", "auto", "Automatico"],
    ["off", "off", "Spento"],
    ["heat", "on", "Acceso · Riscaldamento"],
    ["unavailable", "unavailable", "Non disponibile"],
  ]) {
    state.state = mode;
    card.hass = f.hass;
    const row = card.shadowRoot.querySelector(".room");
    assert.ok(row.querySelector(`.status-icon.${css}`));
    assert.match(row.textContent, new RegExp(label));
    assert.match(row.textContent, /Umidità 0 %/);
    assert.match(row.getAttribute("aria-label"), /umidità 0 per cento/);
  }
  delete state.attributes.current_humidity;
  card.hass = f.hass;
  assert.match(card.shadowRoot.querySelector(".room").textContent, /Umidità —/);
  card.remove();
  f.dispose();
});

test("compact panel never permits schedule writes even when integration writes are enabled", async () => {
  const f = await fixture({ enabled: true });
  f.calls.length = 0;
  f.hass.states["climate.studio"].state = "auto";
  const original = f.hass.callWS;
  f.hass.callWS = async (request) =>
    request.type === "config/entity_registry/list" ? [] : original(request);
  const card = new KdomoThermostatsCard();
  card.setConfig({ entities: ["climate.studio"] });
  card.hass = f.hass;
  document.body.append(card);
  card.shadowRoot.querySelector(".room").click();
  await tick();
  [...card.shadowRoot.querySelectorAll(".tab")]
    .find((x) => x.textContent === "Programmazione")
    .click();
  await tick();
  const inner = card.shadowRoot.querySelector("kdomo-schedule-card").shadowRoot;
  assert.equal(button(inner, "Salva settimana").disabled, true);
  assert.equal(button(inner, "Dividi fascia").disabled, true);
  assert.equal(f.calls.filter((x) => x.service === "get_schedule").length, 1);
  assert.equal(f.calls.filter((x) => x.service === "set_schedule").length, 0);
  card.remove();
  f.dispose();
});

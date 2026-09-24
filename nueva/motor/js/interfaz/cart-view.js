/*
 * Pedido: contador del header, barra fija en celular y panel con 3 pasos:
 *   1. Revisar  ->  2. Datos y envío  ->  3. Confirmar y enviar por WhatsApp
 */
import { escapeHtml, money, plural, readStorage, writeStorage } from "../utils.js";
import { FIELDS } from "../checkout-fields.js";
import { buildOrderMessage, cleanInput, orderLink } from "../whatsapp.js";
import { icon } from "./icons.js";

const CUSTOMER_KEY = "customer";
const MODE_KEY = "purchase-mode";


export function createCartView({ config, channel, cart, pricing, overlays, storagePrefix }) {
  const headerButton = document.querySelector("[data-open-cart]");
  const headerCount = document.querySelector("[data-cart-count]");
  const customerKey = `${storagePrefix}:${CUSTOMER_KEY}`;
  const modeKey = `${storagePrefix}:${MODE_KEY}`;
  // Si la versión de la tienda define "purchaseModes", el cliente elige por mayor o
  // por unidad. Si no, el precio por mayor se aplica solo al llegar a la cantidad.
  const modes = channel.purchaseModes ?? null;
  let purchaseMode = modes ? readStorage(modeKey, null) : "mayor";   // "mayor" | "unidad" | null (sin elegir)
  let step = "review";
  let lastMessage = "";

  // --- barra fija (celular) --------------------------------------------------
  const bar = document.createElement("div");
  bar.className = "cart-bar";
  bar.innerHTML = `
    <button class="cart-bar__button" type="button" data-open-cart>
      <span class="cart-bar__count" data-bar-count>0</span>
      <span class="cart-bar__summary">
        <span class="cart-bar__title">Ver tu pedido</span>
        <span class="cart-bar__detail" data-bar-detail></span>
      </span>
      <span class="cart-bar__cta"><span class="cart-bar__cta-text">Continuar</span> ${icon("chevronRight")}</span>
    </button>`;
  document.body.append(bar);

  // --- panel -----------------------------------------------------------------
  const dialog = document.createElement("dialog");
  dialog.className = "drawer";
  dialog.setAttribute("aria-labelledby", "drawer-title");
  dialog.innerHTML = `
    <div class="drawer__panel">
      <header class="drawer__header">
        <button class="icon-btn drawer__back" type="button" data-back aria-label="Volver" hidden>${icon("chevronLeft")}</button>
        <div>
          <h2 class="drawer__title" id="drawer-title" tabindex="-1">Tu pedido</h2>
          <ol class="steps" aria-label="Pasos del pedido">
            <li data-step-indicator="review">Revisar</li>
            <li data-step-indicator="details">Datos y envío</li>
            <li data-step-indicator="confirm">Enviar</li>
          </ol>
        </div>
        <button class="icon-btn" type="button" data-close aria-label="Cerrar">${icon("close")}</button>
      </header>
      <div class="drawer__body" data-body></div>
      <footer class="drawer__footer" data-footer></footer>
    </div>`;
  overlays.append(dialog);

  const body = dialog.querySelector("[data-body]");
  const footer = dialog.querySelector("[data-footer]");
  const backButton = dialog.querySelector("[data-back]");

  function open() {
    step = "review";
    render();
    dialog.showModal();
    document.body.classList.add("is-locked");
  }

  function close() {
    dialog.close();
  }

  dialog.addEventListener("close", () => document.body.classList.remove("is-locked"));
  // Tocar fuera del panel (sobre el fondo oscuro) lo cierra.
  dialog.addEventListener("click", (event) => { if (event.target === dialog) close(); });
  dialog.querySelector("[data-close]").addEventListener("click", close);
  backButton.addEventListener("click", () => goTo(step === "confirm" ? "details" : "review"));
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-open-cart]")) open();
  });

  function goTo(next) {
    step = next;
    render();
    body.scrollTop = 0;
    dialog.querySelector(".drawer__title").focus?.();
  }

  const currentQuote = () => pricing.quote(cart.lines(), purchaseMode);
  const needsModeChoice = (quote) => Boolean(modes) && quote.canChoose && !purchaseMode;

  // --- resumen (header + barra) ------------------------------------------------
  /** "3 pares" si son todos calzados; "3 productos" si hay indumentaria. */
  function itemsText(count) {
    const onlyFootwear = cart.lines().every((line) => line.product.category !== "indumentaria");
    return onlyFootwear ? plural(count, "par", "pares") : plural(count, "producto");
  }

  function updateSummary({ bump = false } = {}) {
    const count = cart.count();
    const quote = currentQuote();
    // Si todavía no eligió, se muestra el total por mayor como referencia.
    const showWholesale = quote.canChoose && quote.mode !== "unidad";
    headerCount.textContent = String(count);
    headerButton.classList.toggle("has-items", count > 0);
    headerButton.setAttribute("aria-label", count ? `Ver tu pedido, ${itemsText(count)}` : "Ver tu pedido, vacío");
    bar.classList.toggle("is-visible", count > 0);
    bar.querySelector("[data-bar-count]").textContent = String(count);
    bar.querySelector("[data-bar-detail]").textContent = count
      ? `${itemsText(count)} · ${money(showWholesale ? quote.totals.mayor : quote.total)}${showWholesale ? " por mayor" : ""}`
      : "";
    if (bump) {
      for (const el of [headerButton, bar]) {
        el.classList.remove("is-bumped");
        void el.offsetWidth;   // reinicia la animación
        el.classList.add("is-bumped");
      }
    }
  }

  // --- paso 1: revisar ---------------------------------------------------------
  function modeChoice(quote) {
    return `
      <fieldset class="mode-choice" aria-describedby="mode-help">
        <legend class="mode-choice__legend">Llevás ${plural(quote.pairs, "par", "pares")}: ¿cómo querés comprar?</legend>
        <p class="mode-choice__help" id="mode-help">Con ${pricing.minPairs} o más pares surtidos podés elegir.</p>
        <div class="choice-list">
          ${["mayor", "unidad"].map((key) => `
            <label class="choice">
              <input type="radio" name="purchaseMode" value="${key}" ${purchaseMode === key ? "checked" : ""}>
              <span class="choice__box choice__box--row">
                <span>
                  <span class="choice__title">${escapeHtml(modes[key].title)}</span>
                  <span class="choice__text">${escapeHtml(modes[key].note)}</span>
                </span>
                <strong class="choice__price money">${money(quote.totals[key])}</strong>
              </span>
            </label>`).join("")}
        </div>
      </fieldset>`;
  }

  function wholesaleProgress(quote) {
    if (quote.pairs === 0) return "";
    if (quote.canChoose && modes) return modeChoice(quote);
    if (quote.canChoose) {
      const savings = quote.totals.unidad - quote.totals.mayor;
      return `
        <div class="wholesale-meter is-done">
          <p>${icon("check")} <strong>Precio por mayor aplicado</strong>${savings > 0 ? ` · ahorrás <span class="money">${money(savings)}</span>` : ""}</p>
        </div>`;
    }
    const percent = Math.round((quote.pairs / pricing.minPairs) * 100);
    return `
      <div class="wholesale-meter">
        <p>Sumá <strong>${plural(quote.pairsToWholesale, "par", "pares")} más</strong> (surtidos) para el precio por mayor.</p>
        <div class="wholesale-meter__track" role="progressbar" aria-valuemin="0" aria-valuemax="${pricing.minPairs}" aria-valuenow="${quote.pairs}" aria-label="Pares para precio por mayor">
          <span style="width:${percent}%"></span>
        </div>
      </div>`;
  }

  function renderReview() {
    const quote = currentQuote();
    if (!quote.lines.length) {
      body.innerHTML = `
        <div class="state-message state-message--flat">
          ${icon("bag")}
          <h3 class="state-message__title">Tu pedido está vacío</h3>
          <p class="state-message__text">Elegí un talle en cualquier modelo y tocá “Agregar”. Lo vas a ver acá.</p>
        </div>`;
      footer.innerHTML = `<button class="btn btn--primary btn--block btn--lg" type="button" data-close-drawer>Ver catálogo</button>`;
      footer.querySelector("[data-close-drawer]").addEventListener("click", close);
      return;
    }

    body.innerHTML = `
      ${wholesaleProgress(quote)}
      <ul class="cart-lines">
        ${quote.lines.map((line) => {
          const max = cart.maxFor(line.productId, line.size);
          const thumb = line.product.images[0]?.sm;
          return `
            <li class="cart-line" data-line-product="${escapeHtml(line.productId)}" data-line-size="${escapeHtml(line.size)}">
              ${thumb ? `<img class="cart-line__thumb" src="${escapeHtml(thumb)}" alt="" width="60" height="80" loading="lazy">` : `<span class="cart-line__thumb"></span>`}
              <div class="cart-line__info">
                <p class="cart-line__name">${escapeHtml(line.product.name)}</p>
                <p class="cart-line__meta">Talle <strong>${escapeHtml(line.size)}</strong> · <span class="money">${money(line.price)}</span> c/u</p>
                <div class="cart-line__controls">
                  <div class="stepper stepper--sm" role="group" aria-label="Cantidad de ${escapeHtml(line.product.name)} talle ${escapeHtml(line.size)}">
                    <button class="stepper__btn" type="button" data-line-step="-1" aria-label="Restar uno" ${line.qty <= 1 ? "disabled" : ""}>${icon("minus")}</button>
                    <output class="stepper__value">${line.qty}</output>
                    <button class="stepper__btn" type="button" data-line-step="1" aria-label="Sumar uno" ${line.qty >= max ? "disabled" : ""}>${icon("plus")}</button>
                  </div>
                  <button class="cart-line__remove" type="button" data-line-remove>${icon("trash")} Quitar</button>
                </div>
              </div>
              <p class="cart-line__subtotal money">${money(line.subtotal)}</p>
            </li>`;
        }).join("")}
      </ul>
      <p class="drawer__note">${icon("chat")} No se paga online. Te confirmamos el stock por WhatsApp antes de cualquier pago.</p>`;

    const pending = needsModeChoice(quote);
    footer.innerHTML = `
      <div class="drawer__total">
        <span>Total <small>(${itemsText(cart.count())}${quote.canChoose && !pending ? `, ${modes ? modes[quote.mode].title.toLowerCase() : "por mayor"}` : ""}, sin envío)</small></span>
        ${pending ? `<span class="drawer__pending">Elegí por mayor o por unidad</span>` : `<strong class="money">${money(quote.total)}</strong>`}
      </div>
      <button class="btn btn--primary btn--block btn--lg" type="button" data-next ${pending ? "disabled" : ""}>Continuar con el pedido ${icon("arrowRight")}</button>`;
    footer.querySelector("[data-next]").addEventListener("click", () => goTo("details"));
  }

  body.addEventListener("change", (event) => {
    if (event.target.name !== "purchaseMode") return;
    purchaseMode = event.target.value;
    writeStorage(modeKey, purchaseMode);
    render();
    updateSummary();
  });

  body.addEventListener("click", (event) => {
    const lineEl = event.target.closest("[data-line-product]");
    if (!lineEl) return;
    const { lineProduct, lineSize } = lineEl.dataset;
    const stepBtn = event.target.closest("[data-line-step]");
    if (stepBtn) cart.setQty(lineProduct, lineSize, cart.qtyOf(lineProduct, lineSize) + Number(stepBtn.dataset.lineStep));
    if (event.target.closest("[data-line-remove]")) cart.remove(lineProduct, lineSize);
  });

  // --- paso 2: datos y envío ---------------------------------------------------
  function fieldHtml(id, { required, value }) {
    const f = FIELDS[id];
    return `
      <div class="field">
        <label class="field__label" for="f-${id}">${escapeHtml(f.label)}${required ? '<span class="field__required"> *</span>' : ""}</label>
        <input class="field__input" id="f-${id}" name="${id}" type="text" maxlength="${f.max}"
          autocomplete="${f.autocomplete ?? "off"}" placeholder="${escapeHtml(f.placeholder ?? "")}" value="${escapeHtml(value ?? "")}"
          aria-describedby="e-${id}" ${required ? 'aria-required="true"' : ""}>
        <p class="field__error" id="e-${id}"></p>
      </div>`;
  }

  function renderDetails() {
    if (needsModeChoice(currentQuote())) {
      goTo("review");
      return;
    }
    const methods = config.shipping.methods;
    const draft = readStorage(customerKey, {});   // lo que el cliente escribió la vez anterior
    let method = methods[draft.shippingMethod] ? draft.shippingMethod : Object.keys(methods)[0];

    body.innerHTML = `
      <form class="checkout-form" id="checkout-form" novalidate>
        ${fieldHtml("name", { required: true, value: draft.name })}
        <fieldset class="field">
          <legend class="field__label">¿Cómo lo recibís?</legend>
          <div class="choice-list">
            ${Object.entries(methods).map(([key, m]) => `
              <label class="choice">
                <input type="radio" name="shippingMethod" value="${escapeHtml(key)}" ${key === method ? "checked" : ""}>
                <span class="choice__box">
                  <span class="choice__title">${escapeHtml(m.label)}</span>
                  <span class="choice__text">${escapeHtml(m.summary)}</span>
                </span>
              </label>`).join("")}
          </div>
        </fieldset>
        <div class="shipping-fields" data-method-fields></div>
        <p class="drawer__note" data-shipping-note></p>
        <div class="field">
          <label class="field__label" for="f-notes">Comentarios <span class="field__optional">(opcional)</span></label>
          <textarea class="field__input" id="f-notes" name="notes" rows="2" maxlength="${FIELDS.notes.max}">${escapeHtml(draft.notes ?? "")}</textarea>
        </div>
      </form>`;

    footer.innerHTML = `<button class="btn btn--primary btn--block btn--lg" type="submit" form="checkout-form">Revisar mensaje ${icon("arrowRight")}</button>`;

    const form = body.querySelector("form");
    // Al cambiar de método se dibujan sus campos, conservando lo ya escrito.
    const renderMethodFields = () => {
      const current = methods[method];
      form.querySelector("[data-method-fields]").innerHTML = (current.fields ?? [])
        .map((f) => fieldHtml(f.id, { required: f.required, value: draft[f.id] }))
        .join("");
      form.querySelector("[data-shipping-note]").innerHTML = current.checkoutNote ? `${icon("truck")} ${escapeHtml(current.checkoutNote)}` : "";
    };
    form.addEventListener("change", (event) => {
      if (event.target.name !== "shippingMethod") return;
      method = event.target.value;
      renderMethodFields();
    });
    form.addEventListener("input", (event) => {
      const input = event.target;
      if (input.name in FIELDS) draft[input.name] = input.value;
      // El error de un campo se borra apenas el cliente lo completa.
      if (input.getAttribute("aria-invalid") === "true" && input.value.trim().length >= 2) {
        input.setAttribute("aria-invalid", "false");
        form.querySelector(`#e-${input.name}`).textContent = "";
      }
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const customer = validate(form, method);
      if (!customer) return;
      writeStorage(customerKey, customer);
      goTo("confirm");
    });
    renderMethodFields();
  }

  function validate(form, method) {
    const fields = [{ id: "name", required: true }, ...(config.shipping.methods[method].fields ?? []), { id: "notes" }];
    const customer = { shippingMethod: method };
    let firstInvalid = null;
    for (const { id, required } of fields) {
      const input = form.elements[id];
      const value = cleanInput(input.value, FIELDS[id].max);
      const invalid = Boolean(required) && value.length < 2;
      customer[id] = value;
      input.setAttribute("aria-invalid", String(invalid));
      const error = form.querySelector(`#e-${id}`);
      if (error) error.textContent = invalid ? `Completá “${FIELDS[id].label}”.` : "";
      if (invalid && !firstInvalid) firstInvalid = input;
    }
    if (firstInvalid) {
      firstInvalid.focus();
      return null;
    }
    return customer;
  }

  // --- paso 3: confirmar y enviar ----------------------------------------------
  function renderConfirm() {
    const quote = currentQuote();
    const customer = readStorage(customerKey, null);
    if (!quote.lines.length || !customer || needsModeChoice(quote)) {
      goTo("review");
      return;
    }
    lastMessage = buildOrderMessage({ config, channel, quote, customer });
    body.innerHTML = `
      <p class="drawer__lead">Este es el mensaje que se va a enviar. Revisalo y tocá “Enviar por WhatsApp”.</p>
      <pre class="message-preview">${escapeHtml(lastMessage).replace(/\*(.+?)\*/g, "<strong>$1</strong>")}</pre>
      <p class="drawer__note">${icon("chat")} Enviar el pedido no es una compra: te respondemos por WhatsApp para confirmar el stock y coordinar el pago y la entrega.</p>
      <div class="sent-help" data-sent-help hidden>
        <p><strong>¿No se abrió WhatsApp?</strong> Copiá el mensaje y mandalo al ${escapeHtml(formatPhone(config.contact.whatsappOrders))}.</p>
        <div class="sent-help__actions">
          <button class="btn btn--outline" type="button" data-copy>Copiar mensaje</button>
          <button class="btn btn--ghost" type="button" data-clear>Ya lo envié, vaciar pedido</button>
        </div>
      </div>`;
    footer.innerHTML = `
      <a class="btn btn--whatsapp btn--block btn--lg" href="${orderLink(config, lastMessage)}" target="_blank" rel="noopener" data-send>
        ${icon("whatsapp")} Enviar pedido por WhatsApp
      </a>`;
    footer.querySelector("[data-send]").addEventListener("click", () => {
      body.querySelector("[data-sent-help]").hidden = false;
      document.dispatchEvent(new CustomEvent("store:order-sent", { detail: { total: quote.total, items: cart.count() } }));
    });
    body.querySelector("[data-copy]").addEventListener("click", async (event) => {
      try {
        await navigator.clipboard.writeText(lastMessage);
        event.target.textContent = "¡Copiado!";
      } catch {
        event.target.textContent = "No se pudo copiar";
      }
    });
    body.querySelector("[data-clear]").addEventListener("click", () => {
      cart.clear();
      close();
    });
  }

  function render() {
    backButton.hidden = step === "review";
    dialog.querySelectorAll("[data-step-indicator]").forEach((el) => {
      el.classList.toggle("is-current", el.dataset.stepIndicator === step);
      if (el.dataset.stepIndicator === step) el.setAttribute("aria-current", "step");
      else el.removeAttribute("aria-current");
    });
    if (step === "details") renderDetails();
    else if (step === "confirm") renderConfirm();
    else renderReview();
  }

  cart.subscribe((event) => {
    // Si el pedido baja de la cantidad mínima (o se vacía), la elección se vuelve a pedir.
    if (modes && purchaseMode && !pricing.quote(cart.lines()).canChoose) {
      purchaseMode = null;
      writeStorage(modeKey, null);
    }
    updateSummary({ bump: event.type === "add" });
    if (dialog.open && step === "review") render();
  });
  updateSummary();

  return { open, close, updateSummary };
}

function formatPhone(number) {
  const digits = String(number).replace(/\D/g, "");
  const local = digits.replace(/^549/, "");
  return local.length === 10 ? `${local.slice(0, 2)} ${local.slice(2, 6)}-${local.slice(6)}` : digits;
}

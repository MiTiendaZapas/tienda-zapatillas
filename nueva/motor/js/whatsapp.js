/*
 * Mensajes de WhatsApp: pedido completo y consultas.
 * Usa *negrita* de WhatsApp y texto plano, sin emojis que puedan verse mal.
 */
import { FIELDS } from "./checkout-fields.js";
import { money, whatsappLink } from "./utils.js";

/** Limpia texto escrito por el cliente: sin caracteres de control ni saltos de más. */
export function cleanInput(value, maxLength) {
  return String(value ?? "")
    .replace(/[\u0000-\u0008\u000B-\u001F\u007F]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, maxLength);
}

export function buildOrderMessage({ config, channel, quote, customer }) {
  const shipping = config.shipping.methods[customer.shippingMethod];
  const lines = [];

  lines.push(`Hola ${config.name}! Quiero hacer este pedido desde la tienda (${channel.label}):`);
  lines.push("");
  lines.push(`*Cliente:* ${customer.name}`);
  lines.push("");
  lines.push("*Pedido*");
  for (const line of quote.lines) {
    lines.push(`• ${line.product.name} | Talle ${line.size} | x${line.qty} | ${money(line.price)} c/u = ${money(line.subtotal)}`);
  }
  lines.push("");
  lines.push(`Pares: ${quote.pairs}`);
  lines.push(`*TOTAL: ${money(quote.total)}*`);
  // Igual que la tienda actual: la modalidad elegida (y su condición de cambio)
  // se aclara cuando el pedido llega a la cantidad para comprar por mayor.
  if (quote.canChoose) {
    lines.push(channel.purchaseModes
      ? channel.purchaseModes[quote.mode].message
      : `Compra POR MAYOR (${quote.minPairs} o más pares surtidos).`);
  }
  lines.push("");

  lines.push(`*Envío:* ${shipping.label}`);
  // Datos del método de envío elegido, en el orden en que se piden.
  for (const { id } of shipping.fields ?? []) {
    if (customer[id]) lines.push(`${FIELDS[id].messageLabel ?? FIELDS[id].label}: ${customer[id]}`);
  }
  if (shipping.messageNote) lines.push(shipping.messageNote);

  if (customer.notes) {
    lines.push("");
    lines.push(`*Comentarios:* ${customer.notes}`);
  }
  lines.push("");
  lines.push("Quedo a la espera de la confirmación de stock.");
  return lines.join("\n");
}

export function orderLink(config, message) {
  return whatsappLink(config.contact.whatsappOrders, message);
}

export function productQueryLink(config, product, size) {
  const sizeText = size ? ` en talle ${size}` : "";
  return whatsappLink(config.contact.whatsappQueries,
    `Hola ${config.name}! Quería consultar por ${product.name}${sizeText}.`);
}

/*
 * Campos que puede pedir el formulario. Cada método de envío de
 * configuracion.js elige cuáles usa: fields: [{ id: "address", required: true }].
 */
export const FIELDS = {
  name: { label: "Tu nombre", max: 60, autocomplete: "name", placeholder: "Nombre y apellido" },
  address: { label: "Dirección", max: 120, autocomplete: "street-address", placeholder: "Calle y número" },
  city: { label: "Localidad", max: 80, autocomplete: "address-level2", placeholder: "Localidad" },
  reference: { label: "Entre calles o referencia", max: 120, placeholder: "Opcional", messageLabel: "Referencia" },
  branch: { label: "Sucursal de Vía Cargo", max: 120, placeholder: "Nombre o dirección de la sucursal", messageLabel: "Sucursal Vía Cargo" },
  receiver: { label: "Quién retira", max: 60, placeholder: "Opcional, si no retirás vos", messageLabel: "Retira" },
  notes: { label: "Comentarios", max: 300 },
};

/*
 * CONFIGURACIÓN DE LA TIENDA: L.A IMP
 * ---------------------------------------------------------------------------
 * Este es el archivo para personalizar la tienda: nombre, colores, contactos,
 * redes y textos. Los precios están aparte, en precios-mayorista.json y
 * precios-minorista.json.
 *
 * Números de WhatsApp: formato internacional sin "+" ni espacios
 * (54 9 11 xxxx-xxxx  ->  "5491100000000").
 */
window.STORE_CONFIG = {
  id: "la-imp",
  name: "L.A IMP",
  tagline: "Zapatillas importadas de Brasil",

  // Carpeta del catálogo compartido (productos.json + fotos/), relativa a esta página.
  catalogBase: "catalogo/",

  // Orden de los modelos: "marca-modelo" (marca A-Z y modelo A-Z) o "mas-vendidos".
  catalogOrder: "marca-modelo",

  logo: {
    small: "marca/logo-160.webp",
    large: "marca/logo-512.webp",
    alt: "L.A IMP",
  },

  // Colores tomados del logo: negro de fondo, dorado del anillo y las letras,
  // blanco cálido del texto. El rojo de la campera queda para avisos.
  theme: {
    fonts: {
      // Fuentes guardadas dentro del proyecto (no dependen de Google).
      stylesheet: "motor/fuentes/fuentes.css",
      display: "'Barlow Condensed', 'Arial Narrow', sans-serif",
      body: "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
    },
    colors: {
      "bg": "#0a0a0b",
      "surface": "#141416",
      "surface-2": "#1c1c1f",
      "border": "#2a2a2e",
      "text": "#f5f3ee",
      "text-muted": "#a8a39a",
      "accent": "#d8b068",
      "accent-strong": "#f0d88c",
      "accent-contrast": "#16110a",
      "accent-gradient": "linear-gradient(135deg, #f0d88c 0%, #d8b068 45%, #b88030 100%)",
      "danger": "#ef5350",
      "success": "#7bd88f",
    },
    colorScheme: "dark",
  },

  contact: {
    // Consultas (modelos, talles, stock) y pedidos van al mismo número,
    // pero con mensajes distintos para que se reconozcan en el chat.
    whatsappQueries: "5491153773771",
    whatsappOrders: "5491153773771",
  },

  social: [
    { network: "instagram", label: "Instagram", handle: "@lautaroagustin_imp", url: "https://www.instagram.com/lautaroagustin_imp/" },
    { network: "tiktok", label: "TikTok", handle: "@lautaroortiz155", url: "https://www.tiktok.com/@lautaroortiz155" },
    { network: "facebook", label: "Facebook", handle: "L.A IMP", url: "https://www.facebook.com/share/1Dkgvn1k2R/" },
  ],

  // Las dos versiones de la tienda. Cada página HTML indica cuál es con
  // <body data-channel="...">.
  channels: {
    mayorista: {
      label: "Revendedores",
      page: "index.html",
      prices: "precios-mayorista.json",
      // Llevando 5 o más pares el cliente elige cómo comprar (igual que la tienda actual).
      purchaseModes: {
        mayor: { title: "Por mayor", note: "Sin cambio de talle", when: "Llevando 5 o más pares surtidos y eligiendo comprar por mayor.", message: "Compra POR MAYOR (5 o más pares surtidos): sin cambio de talle." },
        unidad: { title: "Por unidad", note: "Cambio de talle con recargo de $5.000", when: "Cuando comprás por unidad (o elegís no comprar por mayor).", message: "Compra POR UNIDAD: cambio de talle con recargo de $5.000." },
      },
      hero: {
        eyebrow: "Venta por mayor",
        title: "Zapatillas importadas",
        highlight: "para tu negocio",
        text: "Elegí modelos y talles, armá tu pedido y envialo por WhatsApp. Confirmamos el stock y coordinamos la entrega con vos.",
        points: [
          { icon: "box", text: "Por mayor llevando 5 o más pares surtidos" },
          { icon: "clock", text: "Stock actualizado durante el día" },
          { icon: "chat", text: "Sin pago online: confirmás por WhatsApp" },
        ],
      },
    },
    minorista: {
      label: "Tienda",
      page: "minorista.html",
      prices: "precios-minorista.json",
      purchaseModes: {
        mayor: { title: "Por mayor", note: "Sin cambio de talle", when: "Llevando 5 o más pares surtidos y eligiendo comprar por mayor.", message: "Compra POR MAYOR (5 o más pares surtidos): sin cambio de talle." },
        unidad: { title: "Por unidad", note: "Con cambio de talle sin cargo", when: "Cuando comprás por unidad (o elegís no comprar por mayor).", message: "Compra POR UNIDAD: con cambio de talle sin cargo." },
      },
      hero: {
        eyebrow: "Importadas de Brasil",
        title: "Tus próximas zapatillas",
        highlight: "a un mensaje",
        text: "Elegí tu modelo y tu talle, armá el pedido y envialo por WhatsApp. Te confirmamos el stock y coordinamos la entrega.",
        points: [
          { icon: "repeat", text: "Cambio de talle sin cargo comprando por unidad" },
          { icon: "truck", text: "Envíos por moto y Vía Cargo" },
          { icon: "chat", text: "Sin pago online: confirmás por WhatsApp" },
        ],
      },
    },
  },

  // Páginas de información (cada una es un archivo dentro de "paginas/").
  // "menu: true" = aparece en el menú de arriba; todas aparecen en el footer.
  pages: [
    { id: "como-comprar", label: "Cómo comprar", file: "paginas/como-comprar.html", menu: true },
    { id: "envios", label: "Envíos", file: "paginas/envios.html", menu: true },
    { id: "cambios", label: "Cambios", file: "paginas/cambios-y-devoluciones.html", menu: true },
    { id: "preguntas", label: "Preguntas", file: "paginas/preguntas-frecuentes.html", menu: true },
    { id: "nosotros", label: "Nosotros", file: "paginas/nosotros.html" },
    { id: "revender", label: "Quiero revender", file: "paginas/revender.html" },
  ],

  // Aviso de talles (solo zapatillas y niños; las ojotas no lo muestran).
  sizeNotice: {
    categories: ["zapatillas", "ninos"],
    short: "Talles argentinos.",
    long: "Los talles de la tienda son argentinos. La etiqueta de la caja puede indicar el talle brasilero, que es un número menos: por ejemplo, un 43 argentino viene marcado como 42.",
    example: { store: "43", box: "42" },
  },

  shipping: {
    methods: {
      moto: {
        label: "Moto mensajería",
        icon: "truck",
        summary: "Te lo llevamos a tu dirección. El costo depende del tiempo de viaje.",
        pageText: "El costo depende del tiempo de viaje hasta tu dirección. Te confirmamos el valor exacto por WhatsApp antes de despachar.",
        consultLabel: "Consultar el costo a mi dirección",
        consultMessage: "¿Cuánto sale la moto a mi dirección? Estoy en ",
        checkoutNote: "El costo del envío se calcula por el tiempo de viaje y te lo confirmamos por WhatsApp.",
        messageNote: "Entiendo que el costo de la moto se confirma por WhatsApp.",
        // Datos que se piden al elegir este método (ver motor/js/checkout-fields.js).
        fields: [{ id: "address", required: true }, { id: "city", required: true }, { id: "reference" }],
      },
      viacargo: {
        label: "Vía Cargo",
        icon: "box",
        summary: "Despachamos a la sucursal de Vía Cargo que elijas. El envío se paga al retirar.",
        points: [
          "Despachamos a la sucursal de Vía Cargo que nos indiques.",
          "El costo del envío no está incluido en el pedido: depende del despacho.",
          "Lo pagás directamente en la sucursal al retirar.",
          "Al hacer el pedido, indicá la localidad y la sucursal donde querés recibirlo.",
        ],
        checkoutNote: "El costo de Vía Cargo no está incluido en el total: lo pagás en la sucursal al retirar.",
        messageNote: "Entiendo que el envío de Vía Cargo no está incluido y lo pago al retirar.",
        fields: [{ id: "city", required: true }, { id: "branch", required: true }, { id: "receiver" }],
      },
      retiro: {
        label: "Retiro / a coordinar",
        icon: "chat",
        summary: "Coordinamos por WhatsApp el punto y el horario de entrega.",
        checkoutNote: "Coordinamos el retiro por WhatsApp cuando confirmemos el stock.",
        messageNote: "",
        fields: [],
      },
    },
    // Tabla de tarifas que se muestra en la página de envíos, dentro del método "ratesFor".
    ratesFor: "moto",
    rates: [
      { max: 10, label: "10 min", price: 6000 },
      { max: 15, label: "15 min", price: 7000 },
      { max: 20, label: "20 min", price: 8000 },
      { max: 25, label: "25 min", price: 9000 },
      { max: 30, label: "30 min", price: 10000 },
      { max: 35, label: "35 min", price: 12000 },
      { max: 45, label: "40 a 45 min", price: 15000 },
      { max: 55, label: "50 a 55 min", price: 17000 },
      { max: 60, label: "1 hora", price: 20000 },
      { max: 90, label: "1 hora y media", price: 30000 },
    ],
  },

  // ---------------------------------------------------------------------------
  // TEXTOS DE LAS PÁGINAS DE INFORMACIÓN
  // En preguntas frecuentes, "channels" limita una pregunta a una sola versión.
  // Para sacar una página, quitala de "pages" (arriba).
  // ---------------------------------------------------------------------------
  howToBuy: {
    title: "Cómo comprar",
    lead: "Armás el pedido en la tienda y lo terminamos juntos por WhatsApp. No se paga nada en la web.",
    steps: [
      { title: "Elegí modelo y talle", text: "Tocá el talle en cada modelo y agregalo a tu pedido. Podés sumar todos los pares que quieras." },
      { title: "Revisá tu pedido", text: "En “Tu pedido” ves el total. Llevando 5 o más pares surtidos elegís si comprás por mayor o por unidad." },
      { title: "Envialo por WhatsApp", text: "Completás tu nombre y cómo lo recibís, y se arma el mensaje con todo el detalle." },
      { title: "Confirmamos y coordinamos", text: "Verificamos el stock real, te confirmamos el pedido y coordinamos el pago y la entrega." },
    ],
  },

  shippingSection: {
    title: "Envíos",
    lead: "Elegís cómo recibirlo al armar el pedido. El costo del envío no está incluido en el total.",
  },

  exchanges: {
    title: "Cambios y devoluciones",
    lead: "Depende de cómo hiciste la compra. Todos los cambios se coordinan por WhatsApp.",
    faultNote: "Si un par tiene una falla de fábrica, lo cambiamos: comprando por mayor o por unidad.",
  },

  resellers: {
    title: "¿Querés empezar a vender zapatillas?",
    lead: "Te acompañamos desde el primer pedido. Con 5 pares surtidos ya accedés al precio por mayor, y te asesoramos para que elijas bien con qué arrancar.",
    points: [
      { icon: "box", title: "Por mayor desde 5 pares", text: "Surtidos: podés combinar modelos y talles." },
      { icon: "clock", title: "Catálogo actualizado", text: "Stock que se renueva durante el día para ofrecer a tus clientes." },
      { icon: "users", title: "Asesoramiento directo", text: "Te ayudamos a armar tu primer pedido según lo que buscás." },
    ],
    whatsapp: "5491136284751",
    ctaLabel: "Quiero asesoramiento",
    message: "Hola! Quiero empezar a revender zapatillas y me gustaría asesoramiento.",
  },

  about: {
    title: "Nosotros",
    text: [
      "L.A IMP nació hace dos años con una idea simple: acercar zapatillas importadas de Brasil a quienes las usan y a quienes quieren venderlas.",
      "Trabajamos de forma directa y por WhatsApp: armás tu pedido, te confirmamos el stock real y coordinamos la entrega con vos, sin vueltas.",
    ],
    values: [
      { title: "2 años", text: "vendiendo zapatillas importadas" },
      { title: "Trato directo", text: "cada pedido lo confirma una persona" },
      { title: "Por unidad o por mayor", text: "para usar o para revender" },
    ],
  },

  faq: [
    { q: "¿Los talles son argentinos?", a: "Sí, en la tienda los talles están en numeración argentina. La etiqueta de la caja puede indicar el talle brasilero, que es un número menos: un 43 argentino viene marcado como 42. En ojotas no aplica." },
    { q: "¿Cómo hago un pedido?", a: "Elegí el talle en cada modelo y agregalo a tu pedido. Cuando termines, tocá “Tu pedido”, completá tus datos y envialo por WhatsApp. Ahí te confirmamos todo." },
    { q: "¿Cómo pago?", a: "En la web no se paga nada. Primero confirmamos el stock por WhatsApp y después te indicamos cómo pagar." },
    { q: "¿El stock que veo es real?", a: "El catálogo se actualiza varias veces al día, pero el stock final siempre te lo confirmamos por WhatsApp antes de cualquier pago. Si tenés una duda puntual, consultanos." },
    { q: "¿Venden por mayor?", a: "Sí. Llevando 5 o más pares surtidos (podés combinar modelos y talles) accedés al precio por mayor, que figura debajo del precio de cada modelo." },
    { q: "¿Cuánto cuesta la moto?", a: "Depende del tiempo de viaje hasta tu dirección: va de $6.000 (10 minutos) a $30.000 (1 hora y media). Te confirmamos el valor exacto por WhatsApp. Mirá la tabla en la sección Envíos." },
    { q: "¿Cómo funciona Vía Cargo?", a: "Despachamos a la sucursal que nos indiques y el envío lo pagás al retirar. El costo no está incluido en el pedido porque depende del despacho." },
    { q: "¿Puedo cambiar el talle?", channels: ["mayorista"], a: "Comprando por unidad, sí: el cambio de talle tiene un recargo de $5.000. Comprando por mayor (5 o más pares) no hay cambio de talle. Revisá bien los talles antes de confirmar." },
    { q: "¿Puedo cambiar el talle?", channels: ["minorista"], a: "Comprando por unidad, sí, y sin cargo. Comprando por mayor (5 o más pares) no hay cambio de talle." },
    { q: "¿Hay cambios por falla?", a: "Sí. Si un par tiene una falla de fábrica lo cambiamos, en cualquier tipo de compra. Escribinos por WhatsApp con una foto." },
    { q: "¿Cuánto tarda el pedido?", a: "Depende de la confirmación del stock y del método de envío. Cuando confirmamos tu pedido por WhatsApp te decimos cuándo lo recibís." },
    { q: "¿Cómo puedo empezar a revender?", a: "Escribinos desde la sección “¿Querés empezar a vender zapatillas?” y te asesoramos para armar tu primer pedido." },
  ],

  // Servicio de tiendas online (queda al final, discreto, sin interferir con la compra).
  platformPromo: {
    enabled: true,
    title: "¿Querés una tienda así para tu negocio?",
    text: "Armamos catálogos online a medida para emprendimientos: con tu marca, tus precios y los pedidos directo a tu WhatsApp.",
    whatsapp: "5491153773771",
    ctaLabel: "Consultar",
    message: "Hola! Vi la tienda de L.A IMP y me interesa una tienda así para mi negocio.",
  },

  footer: {
    description: "Zapatillas importadas de Brasil, por unidad y por mayor. Pedidos por WhatsApp.",
    legal: "Los pedidos se confirman por WhatsApp. No se realizan cobros en este sitio.",
  },

  categories: {
    zapatillas: "Zapatillas",
    ninos: "Niños",
    ojotas: "Ojotas",
    indumentaria: "Indumentaria",
  },
};

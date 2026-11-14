const tienda = db.getSiblingDB("tienda");

// Usuarios ficticios para pruebas de autenticación
tienda.usuarios.insertMany([
    { username: "alice", password: "clave123" },
    { username: "bob", password: "demo456" }
]);

// Pedidos ficticios para pruebas CRUD
tienda.pedidos.insertMany([
    { producto: "Portátil", cantidad: 2 },
    { producto: "Teclado", cantidad: 5 },
    { producto: "Ratón", cantidad: 3 }
]);
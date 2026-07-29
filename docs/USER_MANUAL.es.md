# ValenciaGuard — Manual de usuario (español)

> Para tres roles: **superusuario** (responsable de la agencia), **empleado** (administrador de fincas) y **propietario**.
> Dirección del sistema: https://valenciaguard.duckdns.org/

---

## 1. Operaciones comunes (todos los roles)

### Iniciar sesión
1. Abra https://valenciaguard.duckdns.org/ — será redirigido a la página de acceso.
2. Introduzca su usuario y contraseña (los proporciona el superusuario o un empleado).
3. ¿Olvidó la contraseña? Pida a un administrador que la restablezca; la nueva contraseña se muestra una sola vez.

### Cambiar el idioma
Arriba a la derecha (en la página de acceso, abajo): **ES | EN | 中文**. El sistema recuerda su elección.

### Instalar como aplicación en el móvil
- **Android (Chrome)**: abra la web → menú (tres puntos) → «Añadir a pantalla de inicio».
- **iPhone (Safari)**: abra la web → botón Compartir → «Añadir a pantalla de inicio».

Aparecerá un icono azul «VG»; la app se abre a pantalla completa, sin barra del navegador.

---

## 2. Superusuario (responsable de la agencia)

Tiene todas las funciones de un empleado (sección 3) y además la **gestión de cuentas de empleados**:

### Crear cuentas de empleado
1. Vaya a **Usuarios**.
2. En «Añadir usuario»: nombre de usuario, rol **admin** y contraseña inicial (el botón «generar» crea una segura).
3. Entregue las credenciales al empleado y pídale que cambie la contraseña pronto.

### Restablecer / eliminar cuentas
- Puede restablecer la contraseña de cualquier usuario (se muestra una sola vez).
- Puede eliminar empleados y propietarios; **no puede eliminarse a sí mismo**, por lo que siempre queda al menos un superusuario.

> Solo usted puede crear, restablecer o eliminar cuentas de **empleados (admin)**; los empleados no pueden gestionar a otros empleados.

---

## 3. Empleado (administrador de fincas / admin)

Tras iniciar sesión, la barra superior ofrece:

| Función | Para qué sirve |
|---|---|
| **Dashboard** | Nº de propiedades, ocupación, cobros del mes/año, rentas atrasadas, avisos próximos e incidencias abiertas |
| **Propiedades** | Alta/edición/baja de inmuebles; en la ficha: inquilino, contrato, cobros, documentos e incidencias |
| **Calendario** | Fechas clave: fin de contrato, plazo de preaviso, actualización de renta, vencimiento de seguro, cobros |
| **Propietarios** | Fichas de propietarios (nombre, email, teléfono, WeChat, notas) |
| **Usuarios** | Crear cuentas de acceso para **propietarios** (rol owner, vinculable a su ficha) y restablecer sus contraseñas |
| **Calculadora de renta** | Calcula la subida máxima legal según el IRAV |
| **Asistente AI** | Preguntas sobre la LAU, redacción de cartas al inquilino en español, traducción de presupuestos al chino |
| **Configuración** | Nombre de la empresa, email de avisos, umbral de gasto, tipo IRAV y registro de auditoría |

### Flujos de trabajo habituales
1. **Nuevo propietario**: ficha en Propietarios → cuenta en Usuarios (rol owner, vinculada) → enviar credenciales.
2. **Nuevo inmueble**: Propiedades → Nueva → ficha con inquilino y contrato. Las fechas LAU (duración obligatoria, preaviso, próxima actualización) se calculan solas.
3. **Cobros**: en la ficha del inmueble, registre la renta de cada mes y márquela como cobrada al recibir el pago.
4. **Incidencias**: al crear una incidencia, la IA sugiere urgencia, responsable (propietario/inquilino) y un borrador de respuesta en español para el inquilino. Los gastos por encima del umbral requieren aprobación del propietario.
5. **Documentos**: suba contratos, fianzas y seguros en la ficha; el sistema intenta extraer automáticamente los datos clave del contrato.

---

## 4. Propietario (owner)

Al entrar verá el **portal del propietario** (disponible en 中文, ES y EN):

### Inicio
- Tarjetas resumen: propiedades, renta del mes, ocupación e incidencias pendientes.
- Lista «Mis propiedades» con acceso a **Ver detalles**.

### Ficha del inmueble
- **Estado del contrato**: tipo, fecha de inicio, renta mensual y cuenta atrás de fechas clave (días restantes o vencidos).
- **Cobros**: renta mensual prevista, cobrada y estado (pagada / pendiente / atrasada).
- **Incidencias**: averías del inmueble y su progreso.
- **Documentos**: contratos y seguros descargables.
- **Informe mensual**: botón **«Descargar informe del mes (PDF)»** — genera un informe en chino, listo para guardar o reenviar.

### Qué NO puede hacer el propietario
Solo **consulta** sus propios inmuebles, cobros, incidencias y documentos; no puede modificar datos ni ver información de otros propietarios. Para cualquier gestión (nueva avería, nuevo contrato), contacte con la agencia.

---

## 5. Consejos de seguridad

- Cambie las contraseñas iniciales (p. ej. admin123) lo antes posible.
- No comparta cuentas: cada empleado y cada propietario debe tener la suya, para que la auditoría sea fiable.
- Las contraseñas deben tener al menos 8 caracteres; use el botón «generar» para crear aleatorias.

// V4.3: consulta de pertenencia a JJVV y cargo al elegir el vecino (solo lectura).
(function () {
  var sel = document.getElementById("id_vecino");
  var caja = document.getElementById("jjvv-resultado");
  if (!sel || !caja) return;
  function consultar() {
    if (!sel.value) { caja.className = "aviso aviso-info"; caja.textContent = "Seleccione un vecino para consultar su junta de vecinos y cargo."; return; }
    caja.textContent = "Consultando…";
    fetch(caja.dataset.url.replace("{id}", encodeURIComponent(sel.value)), { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        if (d.con_cargo) {
          caja.className = "aviso aviso-ambar";
          caja.textContent = d.texto + ". El vecino tiene cargo en la junta: se le informa y puede continuar con el ingreso.";
        } else {
          caja.className = "aviso aviso-info";
          caja.textContent = d.texto + ". Puede ingresar la solicitud.";
        }
      })
      .catch(function () { caja.className = "aviso aviso-rojo"; caja.textContent = "No se pudo consultar la junta de vecinos. Puede continuar; la consulta se registra al guardar."; });
  }
  sel.addEventListener("change", consultar);
  if (sel.value) consultar();
})();

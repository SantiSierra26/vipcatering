window.addEventListener("load", function () {
    const imagen = document.getElementById("sobrepuesta");
    imagen.style.opacity = 0;

    let opacidad = 0;
    const duracion = 2000; // duración total en milisegundos (2s)
    const pasos = 100;
    const intervalo = duracion / pasos;

    setTimeout(function () {
        const fadeIn = setInterval(function () {
            opacidad += 1 / pasos;
            imagen.style.opacity = opacidad;

            if (opacidad >= 1) {
                clearInterval(fadeIn);
                imagen.style.opacity = 1; // aseguramos el valor final
            }
        }, intervalo);
    }, 1000); // espera inicial de 1s antes de empezar
});

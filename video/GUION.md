# Guion del video – Laboratorio 9 (2 voces)

Video: `lab9_video.mp4` · duración 11:01 · sin audio. **Voz 1** narra la Parte 1 y cómo se montó la Parte 2; **Voz 2** narra las pruebas de la Parte 2, los resultados y las preguntas.
Cada bloque dura lo suficiente para leer el texto a ritmo tranquilo; `guion.srt` tiene los mismos textos con tiempos (se puede cargar en el reproductor o en el editor como subtítulos para leer mientras se graba).

## Voz 1 – Parte 1 (vertical, Azure) y montaje de la Parte 2 (00:00 – 05:41)

**00:00 – 00:18** · _portada_

Hola. Este es el laboratorio nueve de Arquitecturas de Software: escalamiento vertical y horizontal. En la primera parte mostramos el escalamiento vertical que hicimos en Azure, y en la segunda, el escalamiento horizontal con un balanceador de carga.

**00:18 – 00:49** · _escenario_

El escenario de calidad dice que, cuando varios usuarios piden al mismo tiempo un número de Fibonacci mayor a un millón, todas las peticiones deben responderse y la CPU no puede pasar del setenta por ciento. La aplicación es un servicio en Node que calcula el enésimo número con una función muy ineficiente: fibonacci de seis responde ocho, pero fibonacci de un millón tiene más de doscientos mil dígitos.

**00:49 – 01:21** · _recursos_

Creamos la máquina virtual VERTICAL-SCALABILITY con Ubuntu, en la región Chile Central. Como los tamaños B no estaban disponibles, usamos DS1 v2, con un vCPU, y luego DS2 v2, con dos. Junto con la VM, Azure crea cinco recursos más: el disco del sistema operativo, la interfaz de red, la IP pública, la red virtual con su subred y el grupo de seguridad de red, que funciona como firewall.

**01:21 – 01:51** · _ssh_

Instalamos Node con nvm, clonamos el repositorio y dejamos la aplicación corriendo con forever. Si la lanzamos solo con node, se cae al cerrar SSH, porque el proceso es hijo de la sesión y recibe la señal SIGHUP. Y hay que crear una regla de entrada para el puerto tres mil, porque el grupo de seguridad bloquea por defecto todo el tráfico que llega desde Internet.

**01:51 – 02:21** · _tiempos_

Medimos los tiempos para n entre un millón y un millón noventa mil. Cada petición tarda entre nueve y diez segundos, y casi lo mismo en la máquina de dos núcleos. Tarda tanto porque hace un millón de sumas con números de unos doscientos nueve mil dígitos, con una librería de enteros grandes escrita en JavaScript, en un solo hilo y sin reutilizar nada entre peticiones.

**02:21 – 02:52** · _cpu_

Esta es la métrica de CPU de Azure Monitor. Con un vCPU, la CPU llega casi al cien por ciento, porque el cálculo es puro procesamiento. Con dos vCPU se queda en cincuenta por ciento: Node ejecuta el JavaScript en un solo hilo, así que usa un núcleo y el otro queda sin hacer nada. En los dos casos, el núcleo que trabaja supera el setenta por ciento.

**02:52 – 03:29** · _newman_

Con newman lanzamos dos y luego cuatro ejecuciones en paralelo, de diez peticiones cada una. Con dos clientes solo se respondió entre el sesenta y cinco y el setenta por ciento, y con cuatro, alrededor de la mitad. El tiempo promedio se duplica, porque las peticiones hacen cola. Todos los fallos son ECONNRESET: mientras el único hilo está ocupado con la petición de otro cliente, Node cierra tarde las conexiones keep-alive, y el cliente pierde la petición que ya había enviado.

**03:29 – 04:02** · _tamanos_

Sobre los tamaños: B1ls tiene un vCPU y medio giga de RAM, y B2ms dos vCPU y ocho gigas, a unas quince veces el precio. Pero la diferencia importante es que la serie B es burstable: acumula créditos de CPU cuando está por debajo de su rendimiento base, y los gasta en ráfagas. Con una carga sostenida como esta, una B1ls se queda sin créditos y la limitan al cinco por ciento.

**04:02 – 04:33** · _concl vertical_

Entonces, ¿aumentar el tamaño sirvió? No. Los tiempos y la tasa de éxito fueron prácticamente iguales, porque la aplicación no puede usar el segundo núcleo. Además, para cambiar el tamaño Azure reinicia la VM: el servicio se cae, forever no vuelve a arrancar solo, y seguimos con un único punto de falla. Con cuatro clientes tampoco mejoró. Conclusión: con escalamiento vertical no se cumple el escenario de calidad.

**04:33 – 05:03** · _azure p2_

En la segunda parte construimos en Azure el balanceador de carga Standard, con su IP pública redundante entre zonas, el backend pool, el health probe, la regla de balanceo del puerto ochenta al tres mil, la red virtual, el grupo de seguridad y la primera máquina virtual. Al crear la segunda y la tercera, Azure respondió que la suscripción estaba deshabilitada: se habían acabado los créditos.

**05:03 – 05:41** · _simulacion_

Por eso reprodujimos la misma arquitectura en un computador local. Cada máquina virtual es un proceso de la aplicación fijado a un único núcleo del procesador, como una VM de un vCPU. Delante va un balanceador que reparte las peticiones en round robin, hace el health probe cada cinco segundos y tiene el mismo idle timeout de cuatro minutos que Azure. Para validarlo repetimos la prueba de una sola máquina, y dio exactamente lo mismo que en Azure: once de veinte, con nueve ECONNRESET.

## Voz 2 – Parte 2: pruebas, resultados y preguntas (05:41 – 11:01)

**05:41 – 06:16** · _repeticion v1 1nucleo x4_

Esta es la repetición acelerada de la prueba con una sola máquina y cuatro clientes. El núcleo está todo el tiempo cerca del cien por ciento, las peticiones hacen cola y van apareciendo los errores en rojo. Terminó con veintiuno de cuarenta respondidas, cuarenta y tres segundos de promedio y más de seis minutos de duración.

**06:16 – 06:55** · _repeticion h4 x4_

Ahora, la misma carga con cuatro máquinas detrás del balanceador. Cada petición va a una máquina distinta, las cuatro trabajan en paralelo, cada una con su núcleo, y casi no hay errores. También se ve que el health probe marca los nodos como no disponibles mientras calculan, porque no alcanzan a contestar. Resultado: treinta y cinco de cuarenta, diecisiete segundos de promedio, y la mitad del tiempo total.

**06:55 – 07:26** · _comparativo_

Este es el comparativo. En naranja, el escalamiento vertical en Azure; en azul, la simulación. Con una sola máquina, de uno o de dos núcleos, se responde alrededor de la mitad. Con tres máquinas y dos clientes se respondió el cien por ciento, con doce segundos de promedio, prácticamente lo que tarda una petición sola. Y con cuatro máquinas y cuatro clientes, el ochenta y ocho por ciento.

**07:26 – 07:49** · _cpu vm_

Y esta es la CPU de cada máquina. Con escalamiento vertical a dos núcleos, la CPU se queda en cincuenta por ciento sin mejorar nada. Con escalamiento horizontal, cada máquina usa su núcleo completo cuando tiene trabajo y descansa cuando no, así que la carga se reparte entre todas.

**07:49 – 08:16** · _costos_

En costos, una DS2 v2 sale en unos ciento diez dólares al mes, y tres DS1 v2 con el balanceador, en unos ciento ochenta. El esquema horizontal es más caro por hora, pero es el único que cumple el requisito, tolera la caída de una máquina o de una zona completa, y crece agregando nodos sin apagar el servicio.

**08:16 – 08:50** · _porque_

¿Por qué aumenta la tasa de éxito? Porque cada instancia de Node solo atiende una petición pesada a la vez. Con más instancias, cada una con su propio hilo y su propio núcleo, las peticiones se procesan en paralelo en lugar de hacer cola, y desaparecen los cierres de conexión que causaban los errores. Los pocos fallos con cuatro máquinas pasan cuando el round robin manda una petición a un nodo que todavía está ocupado.

**08:50 – 09:32** · _preguntas1_

Ahora las preguntas. Azure tiene el Load Balancer de capa cuatro, público o interno; Application Gateway, de capa siete; y Front Door y Traffic Manager para balanceo global. El SKU es el nivel del producto: Basic, sin zonas ni SLA, y Standard, el que usamos, con zonas, SLA y seguro por defecto. El balanceador público necesita una IP pública porque es la única entrada al sistema. El backend pool es el conjunto de máquinas que reciben el tráfico, y el health probe revisa cuáles están sanas para no mandarle peticiones a una caída.

**09:32 – 10:18** · _preguntas2_

La regla de balanceo une el frontend, el pool, los puertos y el probe. La persistencia puede ser ninguna, por IP del cliente, o por IP y protocolo; pegar un cliente a un nodo ayuda con sesiones en memoria, pero desbalancea la carga, por eso es mejor una aplicación sin estado. La red virtual es la red privada, con su espacio de direcciones dividido en subredes. Las zonas de disponibilidad son datacenters independientes: con tres, la caída de uno solo tumba un nodo, y una IP zone-redundant sigue funcionando aunque caiga una zona. Y el grupo de seguridad filtra el tráfico permitido.

**10:18 – 10:41** · _diagrama_

Este es el diagrama de despliegue: el cliente llega a la IP pública del balanceador por el puerto ochenta, la regla lo envía al backend pool, y de ahí a las máquinas en tres zonas distintas, dentro de la misma red virtual y protegidas por el grupo de seguridad.

**10:41 – 11:01** · _conclusion_

En conclusión: el escalamiento vertical no resolvió el problema, porque la aplicación solo usa un núcleo. El escalamiento horizontal con un balanceador sí: con suficientes nodos se respondieron todas las peticiones. Todo el código, los datos y las gráficas están en el repositorio. Gracias.

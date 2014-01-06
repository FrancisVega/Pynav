Pynav
==============



<b>¿Qué es Pynav?

Pynav es un script escrito en python que se ejecuta en el terminal del sistema osx, windows o linux. No, aun no tiene GUI.

<b>¿Para qué sirve Pynav?

Su uso más común es convertir una lista de imágenes contenidas en un directorio —psd, png y jpg entre otros—, en archivos html con esas mismas imágenes embebidas, para ser vistas en un navegador de una forma sencilla (en monitor o móvil) haciendo click/tab en cada imagen.

<b>¿Y para eso un script?

Se llama Pynav y si no te gusta no mires.

<b>Vale, ¿hace algo más?

No mucho más, aunque ahora veremos las opciones de Pynav con lo que es posible hacerse una idea de algunas cosas más que nos permite hacer cuando creamos los htmls.

<b>¿Necesito algo más a parte de Pynav?

Sí, necesitas tener instalado imagemagick, si usas Photoshop CC 14.1.2 viene instalado. Si no te lo pudes bajar de <a href="http://www.imagemagick.org">imagemagick.org</a>


<b>Usando Pynav
==============

Pynav se usa en consola así que toca abrir un terminal y escribir. Si escribirmos lo siguiente obtendremos un listado de las opciones que nos permite Pynav:

<b>pynav -h

Se puede empezar a usar Pynav muy rápidamente y sin escribir poco más que el nombre del propio programa y la ruta donde tenemos nuestros psds.

Antes de entrar en las opciones veamos un ejemplo (caso hipotético) que puede ser el uso más común.

<b>pynav c:\proyectos\web\Yates-HC

Si introducimos eso en el terminal y pulsamos enter, Pynav creará una presentación de los archivos .psds que existan en c:\proyectos\web\Yates-HC en el directorio c:\proyectos\web\Yates-HC\Pynav-2014-01-05 con formato html y jpg

Si te preguntas por qué Pynav busca psds, por qué hace jpgs y por qué guarda la presentación en el directorio ..Pynav-2014-01-05 la respuesta es: Parámetros por defecto.

En Pynav el único parámetro obligatorio es la ruta donde están los archivos de origen con los que queremos hacer la presentación, todo lo demás es opcional además Pynav tiene pre-configurado algunos parametros con valores por defecto. 

Estos valores los podemos cambiar escribiendo unos nuevos en la línea de comandos o escribiendolos en el archivo de configuración si los queremos para siempre.

Veamos el mismo ejemplo añadiendo algunos valores en el comando

<b>pynav -if png -of jpg -q 75 c:\proyectos\web\Yates-HC c:\web\prev1

Lo que haría ahora Pynav es buscar en el directorio c:\proyectos\web\Yates-HC archivos png, guardará la presentación en c:\web\prev1 y los jpgs de la misma tendrán una calidad de compresión de 75 (sobre 100)


Cómo se ejecuta Pynav

Antes de comenzar veamos qué estructura ideal tiene Pynav a la hora de escribir el comando sabiendo que el único requisito es poner el directorio que contiene nuestro archivos originales.

<b>Pynav [parámetros] directorio/de/origen [directorio/de/destino]

Otra opción válida es poner todos los parámetros al final
Pynav directorio/de/origen [directorio/de/destino] [parámetros]


Parámetros
==============

Todos los parámetros tienen dos versiones, la larga que se escribe con -- delante y la forma corta que se escribe poniendo - delante


Por ejemplo para asignar una calidad de 50 podemos escribir --quality 50 o -q 50


<b>-h, --help

Muestra los parámetros y el uso de Pynav en el terminal


<b>-if, --if-format [psd]

Uso: -if png
Establece el formato de imagen que Pynav va a buscar


<b>-of, --out-format [jpg]

Uso: -of png
Establece el formato de imagen de la presentación


<b>-t, --title [Pynav]

Uso: -t “My Title”
Establece el título de la presentación. Este título se usa en los <title> de los htmls y en la página de índice


<b>-fn, --file-name

Uso: -fn “My_Custom_Name”
Establece un nombre común para los archivos de la presentación. Si por ejemplo especificamos --file-name “web-pre” los archivos se llamarán “web-pre_001”, “web-pre_002”, “web-pre_003”, etc...


<b>-q, --quality [100]

Uso: -q 75
Establece la calidad de compresión de los jpgs en un intervalo de [0-100] 0 Es el peor 100 es el mejor


<b>-ow, --overwrite

Sobreescribe los archivos de la presentación si encuentra alguno con el mismo nombre


<b>-v, --verbose

Obtenemos más información del proceso en el terminal


<b>-fp, --full-path

Muestra las rutas completas en el terminal en el proceso


<b>-l, --log-file

Crea un archivo pynav.log de texto donde podremos ver los detalles de la conversión


<b>-index, --index-of-page

Crea un archivo index.html con enlaces a todas las páginas de la presentación a modo de índice


<b>-image, --only-image

Crea solo imágenes en la presentación, presncindiendo de los html.


<b>-m, --mobile

Crea archivos htmls con otro contenido para que se visualice la presentación correctamente en los dispositivos móviles


<b>-slc, --slice  |  default: 4096

Uso: -slc 5000
Establece el alto en pixels que Pynav usará para cortar en trozos las imágenes cuando hagamos presentaciones para los móviles. Esto es útil debido a las limitaciones de algunos navegadores móviles al mostrar imágenes muy garndes


<b>-style, --css-style

Uso: -style “body { background: #F2F2F2; } ul{ margin: 0; } ”
Añade a los archivos html el css que pongamos, podemos usar múltiples css.


<b>-z, --zip

Crea un archivo .zip con la presentación en el directorio de la misma


<b>-f, --flush

Borra todo el contenido de la carpeta de desitono antes de hacer la conversión (para una presentación limpia)

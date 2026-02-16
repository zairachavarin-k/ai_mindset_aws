# Documento de Requisitos - SmartSupply

## Introducción

SmartSupply es un sistema autónomo de resiliencia logística que detecta incidentes críticos (choques, robos, fallas mecánicas, fallas de cadena de frío) en operaciones de entrega y ejecuta reasignación automática de recursos logísticos en menos de 3 minutos. El sistema utiliza arquitectura serverless de AWS con Amazon Bedrock Agents como motor de razonamiento inteligente para toma de decisiones.

### Pain Points del Cliente

Las empresas logísticas enfrentan desafíos críticos:
- **Tiempo de respuesta lento**: Promedio de 45-60 minutos desde detección de incidente hasta reasignación manual
- **Pérdidas económicas**: $50,000-$200,000 USD anuales por incidentes no gestionados eficientemente
- **Impacto en reputación**: 30% de clientes insatisfechos por falta de comunicación proactiva
- **Decisiones subóptimas**: Reasignaciones manuales sin considerar múltiples variables (fatiga, capacidad, prioridad)
- **Falta de visibilidad**: Operadores sin vista en tiempo real del estado de la flota

### Propuesta de Valor

SmartSupply transforma la gestión de incidentes logísticos mediante:
- **Reducción de 95% en tiempo de respuesta**: De 45-60 minutos a < 3 minutos
- **Ahorro anual estimado**: $120,000 USD por reducción de pérdidas y optimización de recursos
- **Automatización inteligente**: Bedrock Agents toma decisiones considerando 15+ variables simultáneamente
- **Visibilidad total**: Dashboard en tiempo real con Location Service y QuickSight
- **Experiencia del cliente mejorada**: Notificaciones proactivas automáticas

El sistema procesa incidentes desde múltiples canales (voz, web, IoT), analiza el impacto en inventario y rutas, y ejecuta acciones correctivas automáticas incluyendo reasignación de camiones, reabastecimiento desde almacén, actualización de rutas y notificación a clientes afectados.

## Glosario

- **Sistema**: SmartSupply - Sistema de Resiliencia Logística
- **Incidente**: Evento crítico que afecta operaciones logísticas (choque, robo, falla mecánica, falla cadena de frío)
- **Bedrock_Agent**: Amazon Bedrock Agent - Motor de razonamiento y toma de decisiones
- **EventBridge**: AWS EventBridge - Bus central de eventos
- **DynamoDB**: Base de datos NoSQL para operaciones transaccionales en tiempo real
- **S3**: Amazon S3 - Almacenamiento de archivos JSON de rutas, incidencias y configuraciones
- **Location_Service**: Amazon Location Service - Servicio de mapas y geolocalización
- **Connect**: Amazon Connect - Servicio de telefonía para entrada de voz y notificaciones salientes
- **Transcribe**: Amazon Transcribe - Servicio de conversión de voz a texto
- **Lambda**: AWS Lambda - Funciones serverless de procesamiento
- **API_Gateway**: AWS API Gateway - Gateway de APIs REST
- **Amplify**: AWS Amplify - Framework de frontend en JavaScript
- **QuickSight**: Amazon QuickSight - Servicio de dashboards y visualización
- **Kinesis**: Amazon Kinesis - Servicio de streaming de datos IoT
- **Almacén**: Almacén físico ubicado en 19.4384405524696, -99.15694882694186
- **Ruta**: Conjunto de paradas de entrega asignadas a un camión
- **Parada**: Punto de entrega con cliente, ubicación, productos y horario
- **Flota**: Conjunto de 4 camiones disponibles con conductores
- **Inventario_Afectado**: Productos dañados o perdidos en un incidente
- **Prioridad_Crítica**: Categorías Farma, Tecnología de alto valor, Salud
- **Nivel_Gravedad**: Clasificación de incidente (Crítico, Alto, Medio, Bajo)
- **Tiempo_Respuesta**: Tiempo desde detección hasta reasignación completa
- **Canal_Entrada**: Medio de reporte de incidente (Voz, Web, IoT)

## Requisitos

### Requisito 1: Detección Multicanal de Incidentes

**Historia de Usuario:** Como conductor o sistema IoT, quiero reportar incidentes críticos por múltiples canales, para que el sistema detecte y procese eventos en tiempo real.

#### Criterios de Aceptación

1. WHEN un conductor llama a Amazon Connect, THE Sistema SHALL transcribir la llamada usando Transcribe y extraer datos del incidente
2. WHEN un usuario envía un formulario web desde Amplify, THE Sistema SHALL recibir el reporte vía API Gateway
3. WHEN un sensor IoT detecta fuerza G > 4.0, THE Sistema SHALL registrar el evento como incidente potencial
4. WHEN se detecta un incidente por cualquier canal, THE Sistema SHALL publicar un evento en EventBridge con estructura estandarizada
5. THE Sistema SHALL capturar: truck_id, tipo_incidente, ubicación GPS, timestamp, nivel_gravedad, descripción

### Requisito 2: Análisis Inteligente con Bedrock Agent

**Historia de Usuario:** Como sistema autónomo, quiero que Bedrock Agent analice incidentes y tome decisiones informadas usando razonamiento multi-paso, para ejecutar la mejor estrategia de reasignación considerando múltiples variables simultáneamente.

#### Criterios de Aceptación

1. WHEN EventBridge publica un evento de incidente, THE Bedrock_Agent SHALL recibir y analizar el evento usando chain-of-thought reasoning
2. THE Bedrock_Agent SHALL consultar DynamoDB para obtener: ruta afectada, inventario del camión, flota disponible, inventario del almacén
3. THE Bedrock_Agent SHALL calcular el impacto: productos afectados, clientes impactados, valor de pérdida, tiempo de retraso estimado
4. THE Bedrock_Agent SHALL priorizar por criticidad: Farma > Salud > Tecnología > Industrial > otros
5. WHEN productos frágiles están involucrados, THE Bedrock_Agent SHALL aumentar la prioridad de reasignación
6. THE Bedrock_Agent SHALL considerar simultáneamente: nivel de fatiga de conductores, capacidad de carga, distancia desde almacén, tráfico estimado, horarios de entrega comprometidos
7. THE Bedrock_Agent SHALL generar un plan de acción con: camión de reemplazo, productos a reabastecer, rutas actualizadas, justificación de decisiones
8. THE Bedrock_Agent SHALL usar herramientas (tools) para: consultar DynamoDB, calcular distancias, actualizar rutas en S3, enviar notificaciones

### Requisito 3: Reasignación Automática de Recursos

**Historia de Usuario:** Como sistema logístico, quiero reasignar automáticamente camiones y rutas, para minimizar el impacto en entregas programadas.

#### Criterios de Aceptación

1. WHEN Bedrock_Agent genera un plan de reasignación, THE Sistema SHALL seleccionar el camión disponible más cercano al incidente
2. WHEN el camión seleccionado tiene capacidad insuficiente, THE Sistema SHALL dividir la carga entre múltiples camiones
3. WHEN el nivel de fatiga del conductor es Alto, THE Sistema SHALL excluir ese camión de la reasignación
4. THE Sistema SHALL actualizar las rutas en DynamoDB con nuevas paradas y horarios ajustados
5. WHEN productos del inventario afectado están disponibles en almacén, THE Sistema SHALL crear orden de reabastecimiento
6. THE Sistema SHALL recalcular horarios de entrega considerando distancias y tráfico

### Requisito 4: Actualización de Base de Datos

**Historia de Usuario:** Como sistema de datos, quiero actualizar automáticamente todas las tablas afectadas, para mantener consistencia en tiempo real.

#### Criterios de Aceptación

1. WHEN se completa una reasignación, THE Sistema SHALL actualizar la tabla de rutas en DynamoDB
2. THE Sistema SHALL actualizar la tabla de incidencias con: incidente_id, truck_id, inventario_afectado, acciones_tomadas
3. THE Sistema SHALL actualizar el inventario del almacén restando productos reasignados
4. THE Sistema SHALL actualizar el estado de paradas afectadas a "Reasignada" o "Cancelada"
5. THE Sistema SHALL registrar timestamp de cada actualización para auditoría
6. WHEN una actualización falla, THE Sistema SHALL reintentar hasta 3 veces antes de escalar

### Requisito 5: Visualización en Tiempo Real

**Historia de Usuario:** Como operador logístico, quiero visualizar incidentes y reasignaciones en un mapa, para monitorear el estado de la flota en tiempo real.

#### Criterios de Aceptación

1. THE Sistema SHALL mostrar la ubicación de todos los camiones en Amazon Location Service
2. WHEN ocurre un incidente, THE Sistema SHALL marcar la ubicación con ícono de alerta en el mapa
3. THE Sistema SHALL mostrar rutas originales y rutas reasignadas con colores diferenciados
4. THE Sistema SHALL actualizar posiciones de camiones cada 30 segundos
5. WHEN un usuario hace clic en un camión, THE Sistema SHALL mostrar: conductor, carga actual, próxima parada, nivel de fatiga
6. WHEN un usuario hace clic en un incidente, THE Sistema SHALL mostrar: tipo, gravedad, inventario afectado, acciones tomadas

### Requisito 6: Dashboard de Monitoreo

**Historia de Usuario:** Como gerente de operaciones, quiero ver métricas y KPIs en un dashboard, para tomar decisiones estratégicas basadas en datos.

#### Criterios de Aceptación

1. THE Sistema SHALL mostrar en QuickSight: total de incidentes por tipo, valor de pérdidas, tiempo promedio de respuesta
2. THE Sistema SHALL mostrar gráfico de incidentes por gravedad (Crítico, Alto, Medio, Bajo)
3. THE Sistema SHALL mostrar tabla de camiones con: estado actual, paradas completadas, paradas pendientes
4. THE Sistema SHALL mostrar inventario del almacén con alertas de stock bajo
5. THE Sistema SHALL actualizar el dashboard cada 60 segundos
6. THE Sistema SHALL permitir filtrar por rango de fechas y tipo de incidente

### Requisito 7: Notificación a Clientes

**Historia de Usuario:** Como cliente final, quiero recibir notificaciones automáticas sobre cambios en mi entrega, para estar informado en tiempo real.

#### Criterios de Aceptación

1. WHEN una parada es reasignada, THE Sistema SHALL identificar clientes afectados desde DynamoDB
2. THE Sistema SHALL generar mensaje personalizado con: nuevo horario estimado, motivo del cambio, número de seguimiento
3. THE Sistema SHALL enviar llamada saliente usando Amazon Connect a clientes de prioridad crítica
4. WHEN la llamada no es contestada, THE Sistema SHALL reintentar después de 15 minutos
5. THE Sistema SHALL registrar en DynamoDB: cliente_id, timestamp_notificación, canal_usado, estado_entrega

### Requisito 8: Restricción de Tiempo de Respuesta y KPIs

**Historia de Usuario:** Como sistema de alta disponibilidad, quiero completar todo el flujo de reasignación en menos de 3 minutos y medir KPIs de negocio, para cumplir con SLA de resiliencia y demostrar ROI.

#### Criterios de Aceptación

1. THE Sistema SHALL completar el flujo desde detección hasta reasignación en menos de 180 segundos
2. THE Sistema SHALL medir Tiempo_Respuesta para cada incidente y registrarlo en DynamoDB
3. WHEN Tiempo_Respuesta excede 180 segundos, THE Sistema SHALL generar alerta en CloudWatch
4. THE Sistema SHALL calcular y registrar KPIs: reducción de tiempo vs proceso manual, valor de pérdidas evitadas, tasa de éxito de reasignaciones
5. THE Sistema SHALL generar reporte mensual con: ahorro estimado en USD, incidentes resueltos automáticamente, tiempo promedio de respuesta
6. THE Sistema SHALL priorizar procesamiento de incidentes de Nivel_Gravedad Crítico
7. THE Sistema SHALL usar arquitectura orientada a eventos para minimizar latencia

### Requisito 9: Simulación de Sensores IoT

**Historia de Usuario:** Como sistema de pruebas, quiero simular eventos de sensores IoT, para validar el flujo completo sin hardware real.

#### Criterios de Aceptación

1. THE Sistema SHALL leer eventos del archivo 4_registro_incidencias.json
2. WHEN sensor_telemetria_g > 4.0, THE Sistema SHALL clasificar como "Choque / Colisión Grave"
3. WHEN sensor_telemetria_g está entre 2.0 y 4.0, THE Sistema SHALL clasificar como "Falla Mecánica"
4. WHEN sensor_telemetria_g < 2.0, THE Sistema SHALL clasificar como "Robo" o "Falla Cadena de Frío"
5. THE Sistema SHALL publicar eventos simulados a Kinesis o directamente a EventBridge
6. THE Sistema SHALL permitir configurar frecuencia de simulación (eventos por minuto)

### Requisito 10: Manejo de Productos Frágiles

**Historia de Usuario:** Como sistema de calidad, quiero priorizar y manejar especialmente productos frágiles, para minimizar daños en reasignaciones.

#### Criterios de Aceptación

1. WHEN un incidente afecta productos con es_fragil=true, THE Sistema SHALL aumentar prioridad de reasignación
2. THE Bedrock_Agent SHALL seleccionar camiones con menor nivel de fatiga para productos frágiles
3. THE Sistema SHALL validar que el camión de reemplazo tenga capacidad adecuada para carga frágil
4. WHEN productos frágiles son reasignados, THE Sistema SHALL notificar al conductor con instrucciones especiales
5. THE Sistema SHALL registrar en DynamoDB el manejo especial aplicado

### Requisito 11: Gestión de Inventario del Almacén

**Historia de Usuario:** Como sistema de inventario, quiero actualizar automáticamente el stock del almacén, para mantener disponibilidad precisa.

#### Criterios de Aceptación

1. THE Sistema SHALL consultar inventario del almacén desde 3_inventario_almacen.csv cargado en DynamoDB
2. WHEN Bedrock_Agent decide reabastecer productos, THE Sistema SHALL verificar cantidad_disponible_almacen
3. WHEN cantidad_disponible_almacen es insuficiente, THE Sistema SHALL generar alerta de stock crítico
4. THE Sistema SHALL actualizar cantidad_disponible_almacen restando productos reasignados
5. THE Sistema SHALL actualizar cantidad_en_ruta sumando productos despachados
6. THE Sistema SHALL registrar ubicacion_pasillo para facilitar picking en almacén

### Requisito 12: Gestión de Archivos de Rutas e Incidencias en S3

**Historia de Usuario:** Como sistema de persistencia, quiero almacenar y versionar archivos JSON de rutas e incidencias en S3, para que Bedrock Agent pueda leer y modificar configuraciones de forma eficiente.

#### Criterios de Aceptación

1. THE Sistema SHALL almacenar archivos JSON de rutas en S3 con estructura: s3://smart-supply-data/rutas/{fecha}/{truck_id}.json
2. THE Sistema SHALL almacenar registro de incidencias en S3 con estructura: s3://smart-supply-data/incidencias/{año}/{mes}/{incidente_id}.json
3. WHEN Bedrock_Agent genera nuevas rutas, THE Sistema SHALL escribir el JSON actualizado en S3
4. THE Sistema SHALL habilitar versionamiento en el bucket S3 para mantener historial de cambios
5. THE Sistema SHALL cargar datos iniciales desde archivos locales (1_rutas_entregas_2026_02_17.json, 4_registro_incidencias.json) a S3 durante inicialización
6. WHEN se actualiza un archivo en S3, THE Sistema SHALL publicar evento en EventBridge para sincronizar DynamoDB
7. THE Bedrock_Agent SHALL tener permisos de lectura/escritura en el bucket S3 mediante IAM roles

### Requisito 13: Sincronización entre S3 y DynamoDB

**Historia de Usuario:** Como sistema de datos, quiero sincronizar automáticamente cambios entre S3 y DynamoDB, para mantener consistencia entre almacenamiento de archivos y base de datos transaccional.

#### Criterios de Aceptación

1. WHEN un archivo JSON de ruta se actualiza en S3, THE Sistema SHALL parsear el JSON y actualizar registros correspondientes en DynamoDB
2. WHEN DynamoDB recibe una actualización de ruta en tiempo real, THE Sistema SHALL generar JSON actualizado y escribirlo en S3
3. THE Sistema SHALL usar DynamoDB para consultas rápidas en tiempo real (< 10ms)
4. THE Sistema SHALL usar S3 para almacenamiento de largo plazo y análisis histórico
5. WHEN ocurre inconsistencia entre S3 y DynamoDB, THE Sistema SHALL considerar DynamoDB como fuente de verdad
6. THE Sistema SHALL implementar Lambda trigger en S3 para detectar cambios en archivos JSON

### Requisito 14: Arquitectura Serverless y Orientada a Eventos

**Historia de Usuario:** Como arquitecto de sistemas, quiero una arquitectura 100% serverless orientada a eventos, para garantizar escalabilidad y bajo costo operativo.

#### Criterios de Aceptación

1. THE Sistema SHALL usar EventBridge como bus central de eventos
2. THE Sistema SHALL implementar todas las funciones de procesamiento con Lambda
3. THE Sistema SHALL usar DynamoDB para operaciones transaccionales y S3 para almacenamiento de archivos
4. THE Sistema SHALL exponer APIs REST mediante API Gateway
5. THE Sistema SHALL desplegar el frontend con Amplify
6. THE Sistema SHALL evitar servidores con estado o instancias EC2
7. WHEN un componente falla, THE Sistema SHALL reintentar automáticamente usando políticas de retry de Lambda

### Requisito 15: Frontend de Monitoreo

**Historia de Usuario:** Como usuario del sistema, quiero un frontend intuitivo en JavaScript, para interactuar con el sistema sin conocimientos técnicos.

#### Criterios de Aceptación

1. THE Sistema SHALL implementar el frontend usando JavaScript con AWS Amplify
2. THE Sistema SHALL mostrar un mapa interactivo con Amazon Location Service
3. THE Sistema SHALL mostrar formulario de reporte de incidentes con campos: truck_id, tipo, ubicación, descripción
4. WHEN un usuario envía el formulario, THE Sistema SHALL validar campos requeridos antes de enviar a API Gateway
5. THE Sistema SHALL mostrar notificaciones en tiempo real de nuevos incidentes
6. THE Sistema SHALL ser responsive y funcionar en dispositivos móviles

### Requisito 16: Escalabilidad y Visión Transformacional

**Historia de Usuario:** Como empresa en crecimiento, quiero que el sistema escale sin incremento proporcional de costos, para soportar expansión de 4 a 100+ camiones.

#### Criterios de Aceptación

1. THE Sistema SHALL soportar crecimiento de flota de 4 a 100 camiones sin cambios arquitectónicos
2. THE Sistema SHALL mantener tiempo de respuesta < 3 minutos independientemente del tamaño de flota
3. THE Sistema SHALL usar auto-scaling de Lambda para manejar picos de 10x en volumen de incidentes
4. THE Sistema SHALL calcular costo por incidente procesado y mantenerlo < $0.50 USD
5. THE Sistema SHALL permitir expansión multi-región para operaciones internacionales
6. THE Sistema SHALL soportar integración con sistemas externos (ERP, WMS) mediante APIs estándar
7. THE Sistema SHALL generar insights predictivos: zonas de alto riesgo, patrones de incidentes, optimización de rutas preventiva

### Requisito 17: Diferenciadores Técnicos y de Negocio

**Historia de Usuario:** Como stakeholder del proyecto, quiero demostrar diferenciadores únicos del sistema, para justificar inversión y posicionamiento competitivo.

#### Criterios de Aceptación

1. THE Sistema SHALL usar Amazon Bedrock con modelos Claude para razonamiento complejo multi-paso
2. THE Sistema SHALL implementar arquitectura event-driven con EventBridge como orquestador central
3. THE Sistema SHALL demostrar integración profunda de 10+ servicios AWS (Bedrock, Connect, Location, Transcribe, Lambda, DynamoDB, S3, EventBridge, API Gateway, Amplify, QuickSight, Kinesis)
4. THE Sistema SHALL incluir capacidad de procesamiento de lenguaje natural en llamadas de voz para extracción automática de datos de incidente
5. THE Sistema SHALL generar documentación automática de decisiones del Bedrock Agent para auditoría y compliance
6. THE Sistema SHALL calcular y mostrar ROI en dashboard: tiempo ahorrado, pérdidas evitadas, eficiencia operativa
7. THE Sistema SHALL incluir modo de simulación para demostración sin afectar datos reales

from langchain_openai import ChatOpenAI
import os
from flask import Flask, jsonify, request
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage
from langchain_openai import OpenAIEmbeddings
from langchain_elasticsearch import ElasticsearchStore
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.prebuilt import create_react_agent

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from typing import Annotated

## datos de trazabilidad
os.environ["LANGSMITH_ENDPOINT"]="https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "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"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "gcpaiagent"
os.environ["OPENAI_API_KEY"] ="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"

def send_email_message(
    to_address: Annotated[str, "Recipient's email address"],
    subject: Annotated[str, "Email subject"],
    body: Annotated[str, "Email body"],):
  """
  Tool to send your response in html format to the user's email address. Include emojis in your response.
  """
  sender_email = "royerick987@gmail.com"
  password = "dbtq wask fcks dctq" 
  #MIME instance
  msg = MIMEMultipart()
  msg['From'] = sender_email #Sender's email
  msg['To'] = to_address
  msg['Subject'] = subject
  msg.attach(MIMEText(body, 'html'))

  server = smtplib.SMTP('smtp.gmail.com', 587)
  server.starttls()
  #Login
  server.login(sender_email, password) #Sender's email
  #send email
  server.sendmail(sender_email, to_address,msg.as_string()
             )
  server.quit()

app = Flask(__name__)


@app.route('/agent', methods=['GET'])
def main():
    #Capturamos variables enviadas
    id_agente = request.args.get('idagente')
    msg = request.args.get('msg')
    print(f"value: {id_agente} y {msg}")
    #datos de configuracion
    DB_URI = 'postgresql://postgres:L~6O"<bgbdlT{L0O@34.61.147.250:5432/postgres?sslmode=disable'
    db_query = ElasticsearchStore(
        es_url="http://34.16.182.210:9200",
        es_user="elastic",
        es_password="BCQ0UvQC7yxHCXNMLoU_",
        index_name="nutricion_y_deporte-data",
        embedding=OpenAIEmbeddings())

    # Herramienta RAG
    retriever = db_query.as_retriever()
    tool_rag =retriever.as_tool(
        name="busqueda_nutricion_ejercicio",
        description="Consulta en la información relacionada con nutrición, dietas, ejercicio físico, entrenamientos, rutinas de gimnasio, y salud deportiva",
    )   
    #Variables de memoria
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
    }
    # Inicializamos la memoria
    with ConnectionPool(
        # Example configuration
        conninfo='postgresql://postgres:L~6O"<bgbdlT{L0O@34.61.147.250:5432/postgres?sslmode=disable',
        max_size=20,
        kwargs=connection_kwargs,
    ) as pool:
        checkpointer = PostgresSaver(pool)
        print("✅ Conexión y pool inicializado correctamente.")
        # Inicializamos el modelo
        model = ChatOpenAI(model="gpt-4.1-2025-04-14", max_tokens=10000)

        # Archivo de rule
        with open('variable/rules.txt', 'r') as file:
            rules = file.read() 

        # Agrupamos las herramientas
        tolkit = [tool_rag, send_email_message]

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", """
                Eres un asesor experto en rutinas de ejercicio y nutrición. Tu objetivo es guiar a los usuarios en la creación de rutinas de ejercicio personalizadas basadas en sus objetivos físicos (por ejemplo, ganar masa muscular, perder peso, mejorar resistencia, etc.) y sugerirles la mejor dieta para acompañar sus entrenamientos.

                Siempre utiliza las herramientas disponibles para obtener la información de rutinas de ejercicio y recomendaciones nutricionales. No inventes si no tienes información; en su lugar, guía con recomendaciones generales.

                Tu estilo debe ser conversacional, motivador y directo. Sé claro y amable, como un entrenador personal que está allí para apoyar al usuario en su progreso. Los puntos clave son:

                1. **Saludo inicial**:
                - Da una bienvenida cercana y motivadora (ej. “¡Hola campeón! ¿Qué rutina de ejercicio necesitas hoy?”).
                - Pregunta al usuario sobre su objetivo físico (ej. ¿Ganar masa muscular, perder peso?).
                - Si no está seguro, ofrece opciones populares de rutinas para cada objetivo.

                2. **Consulta de rutina de ejercicio**:
                - Filtra las rutinas según los objetivos del usuario (ej. fuerza, resistencia, cardio, etc.).
                - Muestra nombre, duración, y número de sesiones de la rutina, destacando las más efectivas según los objetivos.
                - Para cada **ejercicio incluido en la rutina**, incluye una **URL directa de un video de YouTube en español** que muestre cómo realizarlo correctamente (por ejemplo: https://www.youtube.com/watch?v=...).
                - Si hay rutinas con más variedad o más stock, avisa que están disponibles.


                3. **Recomendación de nutrición**:
                - En caso necesario, sugiere una dieta balanceada que complemente el objetivo físico (ej. recomendaciones de proteínas, carbohidratos, y grasas).

                4. **Cierre**:
                - Anima al usuario con frases como “¡Vamos con todo!”, “¡Listo para el entrenamiento!”.
                - Finaliza confirmando si necesitan más información o si quieren ajustar la rutina.

                IMPORTANTE:
                - Siempre consulta a Elasticsearch antes de dar detalles sobre rutinas de ejercicio o planes nutricionales.
                - No hables como robot. Sé fresco, humano, motivador.
        """),
                ("human", "{messages}"),
            ]
        )
        # inicializamos el agente
        agent_executor = create_react_agent(model, tolkit, checkpointer=checkpointer, prompt=prompt)
        # ejecutamos el agente
        config = {"configurable": {"thread_id": id_agente}}
        response = agent_executor.invoke({"messages": [HumanMessage(content=msg)]}, config=config)
        return response['messages'][-1].content


if __name__ == '__main__':
    # La aplicación escucha en el puerto 8080, requerido por Cloud Run
    app.run(host='0.0.0.0', port=8080)
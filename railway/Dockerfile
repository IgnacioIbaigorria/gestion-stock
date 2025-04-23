# Usar PostgreSQL 13
FROM postgres:13

# Configuración de PostgreSQL
ENV POSTGRES_USER=ignacioibaigorria
ENV POSTGRES_PASSWORD=mysecretpassword
ENV POSTGRES_DB=mydb

# Copiar el script de inicialización
COPY init.sql /docker-entrypoint-initdb.d/

# Exponer el puerto de PostgreSQL
EXPOSE 5432

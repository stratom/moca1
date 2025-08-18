#!/bin/bash
# Cambia 'moca' por 'moca1' en archivos de texto,
# guardando copia previa en ./backup y registrando los archivos modificados.

set -euo pipefail

BACKUP_DIR="./backup"
LOG_FILE="$BACKUP_DIR/modified_files.txt"

# Crear carpeta backup y limpiar/crear log
mkdir -p "$BACKUP_DIR"
: > "$LOG_FILE"

# Excluir: .git, la propia carpeta backup y este script
SELF_SCRIPT="$(basename "$0")"

# Buscar SOLO archivos de texto que contengan 'moca'
# y procesarlos uno por uno
find . -type f \
  -not -path "*/.git/*" \
  -not -path "$BACKUP_DIR/*" \
  -not -name "$SELF_SCRIPT" \
  -exec grep -Il 'moca' {} \; | while IFS= read -r file; do
    echo "Cambiando en $file"

    # Crear carpeta espejo dentro de backup y copiar archivo original
    mkdir -p "$(dirname "$BACKUP_DIR/$file")"
    cp -a "$file" "$BACKUP_DIR/$file"

    # Reemplazo en el archivo original
    sed -i 's/moca/moca1/g' "$file"

    # Registrar en el log
    echo "$file" >> "$LOG_FILE"
done

echo "✅ Cambios completados. Copias en '$BACKUP_DIR'."
echo "📝 Lista de archivos modificados: $LOG_FILE"


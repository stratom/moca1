#!/bin/bash
# Script para cambiar todas las referencias de 'moca' por 'moca1' en los archivos del proyecto

find . -type f -not -path "*/.git/*" -not -name "switching.sh" \
    -exec grep -Il 'moca' {} \; | while read file; do
    echo "Cambiando en $file"
    sed -i 's/moca/moca1/g' "$file"
done

echo "✅ Todos los cambios de 'moca' a 'moca1' han sido realizados."

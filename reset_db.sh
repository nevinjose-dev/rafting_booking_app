#!/bin/bash

echo "⚠️ This will delete your existing database permanently!"
read -p "Type 'yes' to continue: " confirm

if [[ "$confirm" == "yes" ]]; then
    echo "Deleting database..."
    rm -f database/booking.db

    echo "Recreating database..."
    python app.py init-only
    echo "✅ Done!"
else
    echo "❌ Cancelled."
fi

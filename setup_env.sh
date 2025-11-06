#!/bin/bash
# Quick script to copy all .env.example files to .env

echo "🔧 Creating .env files from templates..."

for service_dir in services/*/; do
    service_name=$(basename "$service_dir")
    
    if [ -f "$service_dir.env.example" ]; then
        if [ ! -f "$service_dir.env" ]; then
            cp "$service_dir.env.example" "$service_dir.env"
            echo "  ✓ Created .env for $service_name"
        else
            echo "  ⚠️  .env already exists for $service_name (skipping)"
        fi
    fi
done

echo ""
echo "✅ Done! Now edit the .env files with your API keys:"
echo ""
echo "   # Voice Service (Azure Speech)"
echo "   vi services/voice/.env"
echo ""
echo "   # LLM Service (OpenAI)"
echo "   vi services/llm/.env"
echo ""
echo "   # SMS/Call Services (Twilio)"
echo "   vi services/sms/.env"
echo "   vi services/call/.env"
echo ""
echo "Or leave them as-is to use simulated APIs for development."

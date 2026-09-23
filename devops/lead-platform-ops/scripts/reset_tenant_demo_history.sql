-- Сброс демо-истории тенанта перед повторным прогоном seed_demo_crm.py (09.09, «Косы").
-- seed_demo_crm генерит записи/чаты/колокольчик ТОЛЬКО если таблицы тенанта пусты;
-- после первого частичного прогона (например, 1 живой клиент из бота) надо вычистить
-- сгенерированное, иначе история не появится. КЛИЕНТОВ НЕ трогает — сид их доливает сам.
-- ЗАМЕНИТЬ 10 на id тенанта. Применение: write_file → dk.sh docker cp этот файл
-- lead-platform-db-1:/tmp/ → psql -U booking -d booking -f /tmp/r.sql
-- (кавычки/многострочный SQL через dk.sh psql -c НЕ гонять — ломается).
-- ⚠️ Это мутирующая команда в прод-БД → отдельный approval-ход Hermes.
BEGIN;
DELETE FROM appointment_events WHERE appointment_id IN (SELECT id FROM appointments WHERE tenant_id=10);
DELETE FROM reminders WHERE appointment_id IN (SELECT id FROM appointments WHERE tenant_id=10);
DELETE FROM specialist_notifications WHERE appointment_id IN (SELECT id FROM appointments WHERE tenant_id=10);
DELETE FROM appointments WHERE tenant_id=10;
DELETE FROM staff_notifications WHERE tenant_id=10;
DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE tenant_id=10);
DELETE FROM internal_notes WHERE tenant_id=10;
DELETE FROM conversations WHERE tenant_id=10;
DELETE FROM client_events WHERE tenant_id=10;
DELETE FROM retarget_sent WHERE tenant_id=10;
COMMIT;
SELECT 'appts' AS k, count(*) FROM appointments WHERE tenant_id=10
UNION ALL SELECT 'convs', count(*) FROM conversations WHERE tenant_id=10;

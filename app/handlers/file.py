"""Handler for CSV, TSV, and Excel batch file uploads."""

import io
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from app.config import settings
from app.engine.batch import BatchProcessor
from app.engine.converter import ConversionMode
from app.ui.formatters import format_batch_result
from app.ui.keyboards import get_quick_actions_keyboard
from app.utils.logger import logger
from app.utils.validators import validate_file_size


ALLOWED_EXTENSIONS = {".csv", ".tsv", ".txt", ".xlsx", ".xls"}


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle tabular file uploads for batch geoid conversion."""
    if not update.message or not update.message.document:
        return

    doc = update.message.document
    filename = doc.file_name or "dataset.csv"
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        await update.message.reply_html(
            f"⚠️ <b>Unsupported file format:</b> <code>{ext}</code>\n\n"
            f"Please upload a <code>.csv</code>, <code>.tsv</code>, or <code>.xlsx</code> file containing "
            f"<b>Latitude</b> and <b>Longitude</b> columns."
        )
        return

    try:
        # Validate file size
        validate_file_size(doc.file_size or 0)

        # Notify user that processing has started
        status_msg = await update.message.reply_html(
            f"⏳ <i>Downloading and processing <b>{filename}</b> with EGM2008 engine...</i>"
        )

        # Download file content into memory
        file_obj = await context.bot.get_file(doc.file_id)
        byte_array = await file_obj.download_as_bytearray()

        user_mode_str = context.user_data.get("mode", ConversionMode.UNDULATION_ONLY.value)
        mode = ConversionMode(user_mode_str)

        # Process file
        logger.info(f"Processing batch file {filename} ({len(byte_array)} bytes) in mode {mode}")
        batch_result = BatchProcessor.process_file(
            file_content=bytes(byte_array),
            filename=filename,
            mode=mode,
        )

        # Update status message with summary
        summary_html = format_batch_result(batch_result)
        await status_msg.edit_text(summary_html, parse_mode="HTML")

        # Reply with the processed document
        await update.message.reply_document(
            document=io.BytesIO(batch_result.output_bytes),
            filename=batch_result.output_filename,
            caption="📊 EGM2008 Converted Dataset",
            reply_markup=get_quick_actions_keyboard(mode.value),
        )

    except Exception as e:
        logger.error(f"Error processing file '{filename}': {e}", exc_info=True)
        await update.message.reply_html(
            f"❌ <b>Batch Processing Error:</b>\n\n"
            f"{str(e)}\n\n"
            f"💡 <i>Tip: Ensure your file has column headers like <code>latitude</code> / <code>longitude</code> "
            f"and contains valid numeric rows.</i>"
        )

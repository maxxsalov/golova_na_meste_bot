import logging

from aiogram import Router, types

from bot.content import filter_inline_items

logger = logging.getLogger(__name__)

router = Router()


@router.inline_query()
async def handle_inline_query(inline_query: types.InlineQuery) -> None:
    query = inline_query.query or ""
    logger.info(f"Inline query received: '{query}'")

    items = filter_inline_items(query)
    logger.info(f"Filtered to {len(items)} items")

    try:
        results = [
            types.InlineQueryResultArticle(
                id=str(i),
                title=item["title"],
                description=item["description"],
                input_message_content=types.InputTextMessageContent(
                    message_text=item["text"],
                ),
            )
            for i, item in enumerate(items)
        ]

        await inline_query.answer(results, cache_time=30)
        logger.info(f"Answered inline query with {len(results)} results")
    except Exception as e:
        logger.error(f"Failed to answer inline query: {e}", exc_info=True)

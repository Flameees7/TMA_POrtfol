import io
import logging
import math
import uuid
from pathlib import Path
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete, func, select
from backend.app.bot.keyboards.admin_kb import (
    get_admin_main_keyboard,
    get_admin_product_card_keyboard,
    get_admin_product_list_keyboard,
    get_admin_products_menu_keyboard,
    get_cancel_fsm_keyboard,
    get_photo_upload_done_keyboard,
    get_product_status_selection_keyboard
)
from backend.app.bot.states.product_states import ProductAddState, ProductEditState
from backend.app.config import get_settings
from backend.app.database import AsyncSessionLocal
from backend.app.models.product import Product
from backend.app.services.image_service import ImageService

logger = logging.getLogger("bot_admin_products")
settings = get_settings()
router = Router(name="admin_products")

PAGE_SIZE = 6


def get_uploads_dir() -> Path:
    """Ensures and returns the path to the frontend uploads directory."""
    upload_dir = settings.BASE_DIR / "frontend" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


async def get_next_short_sku(db) -> str:
    """
    Generates clean sequential SKU for bot products: A-1, A-2, A-3...
    """
    res = await db.execute(select(Product.external_id).where(Product.external_id.like("A-%")))
    existing_ids = res.scalars().all()
    max_num = 0
    for ext_id in existing_ids:
        parts = ext_id.split("-")
        if len(parts) >= 2 and parts[1].isdigit():
            num = int(parts[1])
            if num > max_num:
                max_num = num
    return f"A-{max_num + 1}"


def delete_product_local_photos(photos_str: str | None) -> None:
    """Deletes uploaded photos associated with a product from disk when product is deleted."""
    if not photos_str:
        return
    for part in photos_str.replace("\n", ",").split(","):
        cleaned = part.strip()
        if not cleaned:
            continue
        if "/static/uploads/" in cleaned or "uploads/" in cleaned:
            filename = cleaned.split("/")[-1]
            file_path = settings.BASE_DIR / "frontend" / "uploads" / filename
            if file_path.exists() and file_path.is_file():
                try:
                    file_path.unlink()
                    logger.info(f"Deleted product image file from disk: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Could not delete image file {file_path}: {e}")


@router.callback_query(F.data == "adm_products_menu")
async def handle_products_menu(callback: CallbackQuery, state: FSMContext):
    """Shows the main product management menu."""
    if callback.from_user.id != settings.ADMIN_CHAT_ID:
        await callback.answer("⛔️ У вас нет прав администратора.", show_alert=True)
        return

    await state.clear()
    text = (
        "📦 <b>Управление товарами</b>\n\n"
        "Здесь вы можете:\n"
        "• ➕ Добавлять новые товары и загружать фото прямо из Telegram\n"
        "• 📋 Редактировать цены, фото и наличие существующих товаров\n"
        "• 🗑 Удалять неактуальные позиции"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=get_admin_products_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm_back_main")
async def handle_back_to_main(callback: CallbackQuery, state: FSMContext):
    """Returns to top-level admin menu."""
    if callback.from_user.id != settings.ADMIN_CHAT_ID:
        return
    await state.clear()
    admin_text = (
        "⚙️ <b>Панель управления магазином</b>\n\n"
        "Выберите раздел для работы:"
    )
    if callback.message:
        await callback.message.edit_text(admin_text, reply_markup=get_admin_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm_fsm_cancel")
async def handle_fsm_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancels current interactive FSM operation."""
    await state.clear()
    await callback.answer("Операция отменена.")
    await handle_products_menu(callback, state)


# ---------------------------------------------------------------------------
# PRODUCT BROWSING AND VIEWING
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("adm_prod_list:"))
async def handle_product_list(callback: CallbackQuery, state: FSMContext):
    """Displays paginated list of store products."""
    if callback.from_user.id != settings.ADMIN_CHAT_ID:
        return

    await state.clear()
    parts = callback.data.split(":")
    page = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

    async with AsyncSessionLocal() as db:
        count_res = await db.execute(select(func.count(Product.id)))
        total_count = count_res.scalar() or 0

        total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
        page = max(0, min(page, total_pages - 1))

        query = select(Product).order_by(Product.id.desc()).offset(page * PAGE_SIZE).limit(PAGE_SIZE)
        res = await db.execute(query)
        products = res.scalars().all()

    if not products:
        text = "📦 <b>В каталоге пока нет товаров.</b>\n\nНажмите «➕ Добавить новый товар» для создания первого товара."
        await callback.message.edit_text(text, reply_markup=get_admin_products_menu_keyboard())
        await callback.answer()
        return

    text = (
        f"📋 <b>Список товаров магазина</b> (Всего: {total_count})\n"
        f"Страница {page + 1} из {total_pages}\n\n"
        f"🟢 — В наличии | 🟡 — Под заказ | 🔴 — Нет в наличии\n"
        f"<i>Нажмите на товар для просмотра и редактирования:</i>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_product_list_keyboard(products, page, total_pages)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_prod_view:"))
async def handle_product_view(callback: CallbackQuery, state: FSMContext):
    """Shows full card of a single product with edit buttons."""
    if callback.from_user.id != settings.ADMIN_CHAT_ID:
        return

    await state.clear()
    prod_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Product).where(Product.id == prod_id))
        product = res.scalar_one_or_none()

    if not product:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    status_ru = "🟢 В наличии" if product.stock_status == "in_stock" else ("🟡 Под заказ" if product.stock_status == "preorder" else "🔴 Нет в наличии")
    photos_count = len(product.photo_list)

    card_text = (
        f"📦 <b>{product.title}</b>\n\n"
        f"• <b>Артикул / ID:</b> <code>{product.external_id}</code>\n"
        f"• <b>Цена:</b> <b>{product.price:,.0f} ₽</b>\n"
        f"• <b>Статус:</b> {status_ru}\n"
        f"• <b>Фотографий:</b> {photos_count} шт.\n\n"
        f"<b>Описание:</b>\n{product.description or '<i>(без описания)</i>'}"
    )

    keyboard = get_admin_product_card_keyboard(product.id, product.is_available, product.stock_status)

    if callback.message:
        await callback.message.edit_text(card_text, reply_markup=keyboard)
    await callback.answer()


# ---------------------------------------------------------------------------
# PRODUCT CREATION (FSM)
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "adm_prod_add")
async def handle_start_add_product(callback: CallbackQuery, state: FSMContext):
    """Starts interactive product creation wizard."""
    if callback.from_user.id != settings.ADMIN_CHAT_ID:
        return

    await state.set_state(ProductAddState.waiting_for_title)
    await state.set_data({"photos": []})

    text = (
        "➕ <b>Добавление нового товара</b> (Шаг 1 из 5)\n\n"
        "Введите <b>название товара</b>:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_fsm_keyboard())
    await callback.answer()


@router.message(ProductAddState.waiting_for_title)
async def process_add_title(message: Message, state: FSMContext):
    """Receives product title."""
    title = message.text.strip() if message.text else ""
    if not title:
        await message.answer("Пожалуйста, отправьте текстовое название товара:", reply_markup=get_cancel_fsm_keyboard())
        return

    await state.update_data(title=title)
    await state.set_state(ProductAddState.waiting_for_description)

    text = (
        f"✓ Название: <b>{title}</b>\n\n"
        "➕ <b>Шаг 2 из 5:</b> Введите <b>описание товара</b>\n"
        "<i>(или отправьте <code>-</code> если описание не требуется)</i>:"
    )
    await message.answer(text, reply_markup=get_cancel_fsm_keyboard())


@router.message(ProductAddState.waiting_for_description)
async def process_add_description(message: Message, state: FSMContext):
    """Receives product description."""
    raw_desc = message.text.strip() if message.text else ""
    description = "" if raw_desc == "-" else raw_desc

    await state.update_data(description=description)
    await state.set_state(ProductAddState.waiting_for_price)

    text = (
        "➕ <b>Шаг 3 из 5:</b> Укажите <b>цену товара в рублях</b>\n"
        "<i>(например: <code>4990</code> или <code>15000</code>)</i>:"
    )
    await message.answer(text, reply_markup=get_cancel_fsm_keyboard())


@router.message(ProductAddState.waiting_for_price)
async def process_add_price(message: Message, state: FSMContext):
    """Receives and validates product price."""
    text_val = message.text.strip().replace(" ", "").replace(",", ".") if message.text else ""
    try:
        price = float(text_val)
        if price < 0:
            raise ValueError()
    except (ValueError, TypeError):
        await message.answer(
            "⚠️ Пожалуйста, введите корректное число для цены (например: <code>2500</code>):",
            reply_markup=get_cancel_fsm_keyboard()
        )
        return

    await state.update_data(price=price)
    await state.set_state(ProductAddState.waiting_for_photos)

    text = (
        f"✓ Цена: <b>{price:,.0f} ₽</b>\n\n"
        "➕ <b>Шаг 4 из 5:</b> 📸 <b>Фотографии товара</b>\n\n"
        "Прикрепите и отправьте фотографии <b>прямо в этот чат</b> (можно несколько по очереди).\n\n"
        "Когда закончите отправку фото — нажмите <b>«✅ Готово»</b> ниже (или <b>«⏭ Пропустить»</b>, если фото пока нет):"
    )
    await message.answer(text, reply_markup=get_photo_upload_done_keyboard(has_photos=False))


@router.message(ProductAddState.waiting_for_photos, F.photo)
async def process_add_photo_upload(message: Message, state: FSMContext, bot: Bot):
    """Handles incoming photos sent by admin for new product, converting to WebP."""
    data = await state.get_data()
    photos_list = data.get("photos", [])

    # Pick the highest resolution photo
    photo_size = message.photo[-1]
    file_info = await bot.get_file(photo_size.file_id)

    # Download in-memory
    file_stream = io.BytesIO()
    await bot.download_file(file_info.file_path, destination=file_stream)
    raw_bytes = file_stream.getvalue()

    uploads_dir = get_uploads_dir()
    filename = f"prod_{uuid.uuid4().hex[:12]}.webp"
    dest_path = uploads_dir / filename

    saved_path = ImageService.process_and_save_webp(raw_bytes, dest_path, max_dimension=1600, quality=85)
    relative_url = f"/static/uploads/{saved_path.name}"
    photos_list.append(relative_url)
    await state.update_data(photos=photos_list)

    count = len(photos_list)
    await message.answer(
        f"📸 Фото #{count} успешно сжато в WebP и сохранено!\nВы можете отправить еще фото или нажать <b>«✅ Готово»</b>:",
        reply_markup=get_photo_upload_done_keyboard(has_photos=True)
    )


@router.callback_query(ProductAddState.waiting_for_photos, F.data.in_(["adm_photo_done", "adm_photo_skip"]))
async def process_add_photos_finish(callback: CallbackQuery, state: FSMContext):
    """Advances from photo upload to stock status selection."""
    data = await state.get_data()
    photos_count = len(data.get("photos", []))

    await state.set_state(ProductAddState.waiting_for_status)

    text = (
        f"✓ Фотографий добавлено: <b>{photos_count} шт.</b>\n\n"
        "➕ <b>Шаг 5 из 5:</b> Выберите <b>статус наличия</b> товара:"
    )
    await callback.message.edit_text(text, reply_markup=get_product_status_selection_keyboard())
    await callback.answer()


@router.callback_query(ProductAddState.waiting_for_status, F.data.startswith("prod_status:"))
async def process_add_status_and_save(callback: CallbackQuery, state: FSMContext):
    """Finalizes product creation and saves it to the database."""
    status_code = callback.data.split(":")[1]
    is_available = status_code in ("in_stock", "preorder")

    data = await state.get_data()
    await state.clear()

    title = data.get("title", "Новый товар")
    description = data.get("description", "")
    price = data.get("price", 0.0)
    photos = ",".join(data.get("photos", []))

    async with AsyncSessionLocal() as db:
        external_id = await get_next_short_sku(db)
        new_product = Product(
            external_id=external_id,
            title=title,
            description=description,
            price=price,
            photos=photos,
            is_available=is_available,
            stock_status=status_code
        )
        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)
        saved_id = new_product.id

    status_ru = "🟢 В наличии" if status_code == "in_stock" else ("🟡 Под заказ" if status_code == "preorder" else "🔴 Нет в наличии")
    success_text = (
        "🎉 <b>Товар успешно добавлен и опубликован в магазине!</b>\n\n"
        f"• <b>Артикул:</b> <code>{external_id}</code>\n"
        f"• <b>Название:</b> <b>{title}</b>\n"
        f"• <b>Цена:</b> {price:,.0f} ₽\n"
        f"• <b>Статус:</b> {status_ru}\n\n"
        "Товар сразу виден покупателям в Telegram Mini App."
    )

    keyboard = get_admin_product_card_keyboard(saved_id, is_available, status_code)
    await callback.message.edit_text(success_text, reply_markup=keyboard)
    await callback.answer("Товар создан!")


# ---------------------------------------------------------------------------
# PRODUCT EDITING
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("adm_prod_price:"))
async def handle_edit_price_start(callback: CallbackQuery, state: FSMContext):
    """Starts price editing for selected product."""
    if callback.from_user.id != settings.ADMIN_CHAT_ID:
        return

    prod_id = int(callback.data.split(":")[1])
    await state.set_state(ProductEditState.waiting_for_new_price)
    await state.update_data(product_id=prod_id)

    text = "💰 Введите <b>новую цену товара в рублях</b> (например: <code>3900</code>):"
    await callback.message.edit_text(text, reply_markup=get_cancel_fsm_keyboard())
    await callback.answer()


@router.message(ProductEditState.waiting_for_new_price)
async def process_edit_price_save(message: Message, state: FSMContext):
    """Saves new price to database."""
    text_val = message.text.strip().replace(" ", "").replace(",", ".") if message.text else ""
    try:
        new_price = float(text_val)
        if new_price < 0:
            raise ValueError()
    except (ValueError, TypeError):
        await message.answer(
            "⚠️ Пожалуйста, введите корректную цену (число):",
            reply_markup=get_cancel_fsm_keyboard()
        )
        return

    data = await state.get_data()
    prod_id = data.get("product_id")
    await state.clear()

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Product).where(Product.id == prod_id))
        product = res.scalar_one_or_none()
        if product:
            product.price = new_price
            await db.commit()
            await db.refresh(product)

    if not product:
        await message.answer("Товар не найден.")
        return

    await message.answer(
        f"✅ <b>Цена товара «{product.title}» успешно обновлена на {new_price:,.0f} ₽!</b>",
        reply_markup=get_admin_product_card_keyboard(product.id, product.is_available, product.stock_status)
    )


@router.callback_query(F.data.startswith("adm_prod_photo:"))
async def handle_edit_photo_start(callback: CallbackQuery, state: FSMContext):
    """Starts photo replacement/addition for selected product."""
    if callback.from_user.id != settings.ADMIN_CHAT_ID:
        return

    prod_id = int(callback.data.split(":")[1])
    await state.set_state(ProductEditState.waiting_for_new_photo)
    await state.update_data(product_id=prod_id)

    text = (
        "📸 <b>Загрузка фотографии для товара</b>\n\n"
        "Отправьте фотографию из галереи в этот чат прямо сейчас:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_fsm_keyboard())
    await callback.answer()


@router.message(ProductEditState.waiting_for_new_photo, F.photo)
async def process_edit_photo_save(message: Message, state: FSMContext, bot: Bot):
    """Saves newly uploaded photo to the product in WebP format."""
    data = await state.get_data()
    prod_id = data.get("product_id")
    await state.clear()

    photo_size = message.photo[-1]
    file_info = await bot.get_file(photo_size.file_id)

    file_stream = io.BytesIO()
    await bot.download_file(file_info.file_path, destination=file_stream)
    raw_bytes = file_stream.getvalue()

    uploads_dir = get_uploads_dir()
    filename = f"prod_{uuid.uuid4().hex[:12]}.webp"
    dest_path = uploads_dir / filename

    saved_path = ImageService.process_and_save_webp(raw_bytes, dest_path, max_dimension=1600, quality=85)
    new_url = f"/static/uploads/{saved_path.name}"

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Product).where(Product.id == prod_id))
        product = res.scalar_one_or_none()
        if product:
            existing = product.photos.strip() if product.photos else ""
            if existing:
                product.photos = f"{existing},{new_url}"
            else:
                product.photos = new_url
            await db.commit()
            await db.refresh(product)

    if not product:
        await message.answer("Товар не найден.")
        return

    await message.answer(
        f"✅ <b>Фотография успешно сжата в WebP и добавлена к товару «{product.title}»!</b>",
        reply_markup=get_admin_product_card_keyboard(product.id, product.is_available, product.stock_status)
    )


@router.callback_query(F.data.startswith("adm_prod_toggle_status:"))
async def handle_toggle_status(callback: CallbackQuery):
    """Cycles through stock statuses: in_stock -> preorder -> out_of_stock -> in_stock."""
    if callback.from_user.id != settings.ADMIN_CHAT_ID:
        return

    prod_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Product).where(Product.id == prod_id))
        product = res.scalar_one_or_none()
        if not product:
            await callback.answer("Товар не найден.", show_alert=True)
            return

        # Cycle status
        if product.stock_status == "in_stock":
            product.stock_status = "preorder"
            product.is_available = True
        elif product.stock_status == "preorder":
            product.stock_status = "out_of_stock"
            product.is_available = False
        else:
            product.stock_status = "in_stock"
            product.is_available = True

        await db.commit()
        await db.refresh(product)

    await handle_product_view(callback, None)


@router.callback_query(F.data.startswith("adm_prod_delete:"))
async def handle_delete_product(callback: CallbackQuery):
    """Deletes product from database and cleans up image files on disk."""
    if callback.from_user.id != settings.ADMIN_CHAT_ID:
        return

    prod_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Product).where(Product.id == prod_id))
        product = res.scalar_one_or_none()
        if product:
            title = product.title
            # Delete local photo files from disk
            delete_product_local_photos(product.photos)
            await db.execute(delete(Product).where(Product.id == prod_id))
            await db.commit()
            await callback.answer(f"Товар «{title[:20]}» и его фото удалены.", show_alert=True)
        else:
            await callback.answer("Товар не найден.")

    # Return to product list
    callback.data = "adm_prod_list:0"
    await handle_product_list(callback, None)

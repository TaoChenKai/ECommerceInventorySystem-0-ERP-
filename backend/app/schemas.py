from datetime import datetime, date
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    nickname: str = ""
    role: str = "staff"


class UserOut(BaseModel):
    id: int
    username: str
    nickname: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- 商品档案 ----------
class CategoryCreate(BaseModel):
    name: str
    remark: str = ""


class SkuIn(BaseModel):
    id: int | None = None
    spec_name: str = ""
    sku_code: str = ""
    barcode: str = ""
    cost_price: float = 0
    sale_price: float = 0
    stock: int = 0


class SkuOut(SkuIn):
    id: int
    spu_id: int

    class Config:
        from_attributes = True


class ProductImageIn(BaseModel):
    id: int | None = None
    img_type: str = "main"          # main=美工图/主图 / detail=详情介绍图
    url: str = ""
    sort: int = 0


class ProductImageOut(ProductImageIn):
    id: int

    class Config:
        from_attributes = True


class SpuCreate(BaseModel):
    name: str
    code: str = ""
    category_id: int | None = None
    category_name: str = ""          # 新分类名：传了则按名自动定位/新建分类
    unit: str = "件"
    weight: float = 0
    weight_unit: str = "千克"
    designer: str = ""               # 设计者
    production_date: date | None = None   # 生产日期（YYYY-MM-DD，可空）
    material: str = ""               # 材质
    image_url: str = ""             # 兼容旧字段，新数据走 images
    remark: str = ""
    skus: list[SkuIn] = []
    images: list[ProductImageIn] = []


class SpuUpdate(SpuCreate):
    pass


class SpuOut(BaseModel):
    id: int
    name: str
    code: str = ""
    category_id: int | None = None
    category_name: str | None = None
    unit: str = "件"
    weight: float = 0
    weight_unit: str = "千克"
    designer: str = ""               # 设计者
    production_date: date | None = None   # 生产日期
    material: str = ""               # 材质
    image_url: str = ""
    remark: str = ""
    created_at: datetime
    sku_count: int = 0
    total_stock: int = 0
    skus: list[SkuOut] = []
    images: list[ProductImageOut] = []


# ---------- 单位字典 ----------
class UnitCreate(BaseModel):
    name: str


class UnitUpdate(BaseModel):
    name: str


class UnitOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# ---------- 渠道 / 出入库 / 库存流水 ----------
class ChannelCreate(BaseModel):
    name: str
    channel_type: str = "platform"      # store=实体店 / platform=电商平台 / other
    remark: str = ""


class ChannelOut(ChannelCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StockOp(BaseModel):
    sku_id: int | None = None
    code: str = ""                      # 扫码/手动：条码、SKU编码、商品编号任一
    quantity: int = 1
    channel_id: int | None = None
    remark: str = ""


class StockLogOut(BaseModel):
    id: int
    sku_id: int
    sku_name: str = ""
    channel_id: int | None = None
    channel_name: str = ""
    log_type: str = ""
    quantity: int = 0
    operator: str = ""
    remark: str = ""
    created_at: datetime

    class Config:
        from_attributes = True


class ChannelStats(BaseModel):
    channel_id: int | None = None
    channel_name: str = ""
    out_qty: int = 0
    out_amount: float = 0
    gross_profit: float = 0


# ---------- 回收站 / 批量删除 ----------
class RecycleBatchRequest(BaseModel):
    """批量操作请求：spu_ids 为货品主键列表（批量软删除/还原/彻底删除共用）"""
    spu_ids: list[int] = []


class StockSummary(BaseModel):
    total_spu: int = 0
    total_sku: int = 0
    total_stock: int = 0
    low_stock_sku: int = 0


# ---------- 采购入库 ----------
class SupplierCreate(BaseModel):
    name: str
    contact: str = ""
    phone: str = ""
    remark: str = ""


class SupplierOut(SupplierCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseItemIn(BaseModel):
    id: int | None = None
    spu_id: int | None = None
    sku_id: int | None = None
    status: str = "existing"        # existing=已建档 / draft=待建档
    quantity: int = 1
    unit_price: float = 0
    sku_name: str = ""              # 已建档商品展示名（仅回显）
    barcode: str = ""               # 已建档商品条码（仅回显）
    draft_name: str = ""
    draft_code: str = ""
    draft_spec: str = ""
    draft_barcode: str = ""
    draft_category: str = ""
    draft_unit: str = "件"
    draft_weight: float = 0
    draft_weight_unit: str = "千克"
    draft_remark: str = ""
    draft_images: list[str] = []


class PurchaseItemOut(PurchaseItemIn):
    id: int
    order_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseCreate(BaseModel):
    supplier_id: int | None = None
    supplier_name: str = ""         # 快捷新增供应商时使用
    purchase_method: str = ""
    order_date: str = ""
    remark: str = ""
    items: list[PurchaseItemIn] = []


class PurchaseUpdate(PurchaseCreate):
    pass


class PurchaseOut(BaseModel):
    id: int
    order_no: str
    supplier_id: int | None = None
    supplier_name: str = ""
    purchase_method: str = ""
    order_date: str = ""
    remark: str = ""
    status: str = "draft"
    operator: str = ""
    confirmed_at: datetime | None = None
    created_at: datetime
    items: list[PurchaseItemOut] = []
    total_qty: int = 0
    total_amount: float = 0

    class Config:
        from_attributes = True


# ---------- 销售出库 ----------
class SaleItemIn(BaseModel):
    id: int | None = None
    sku_id: int | None = None
    quantity: int = 1
    discount: float = 0             # 折扣系数：0=无折扣，0.35=3.5折
    unit_price: float = 0           # 实际销售单价
    sku_name: str = ""              # 已建档商品展示名（仅回显）
    spec_name: str = ""             # 规格（仅回显）
    barcode: str = ""               # 条码（仅回显）


class SaleItemOut(SaleItemIn):
    id: int
    order_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SaleCreate(BaseModel):
    channel_id: int | None = None
    channel_name: str = ""          # 快捷新增渠道时使用（可选）
    buyer: str = ""
    remark: str = ""
    items: list[SaleItemIn] = []


class SaleUpdate(SaleCreate):
    pass


class SaleOut(BaseModel):
    id: int
    order_no: str
    channel_id: int | None = None
    channel_name: str = ""
    buyer: str = ""
    remark: str = ""
    status: str = "draft"
    operator: str = ""
    confirmed_at: datetime | None = None
    invoice_no: str = ""
    invoice_status: str = "uninvoiced"
    receipt_no: str = ""
    created_at: datetime
    items: list[SaleItemOut] = []
    total_qty: int = 0
    total_amount: float = 0

    class Config:
        from_attributes = True


# ---------- 常用发件人（物流标签打印） ----------
class SenderCreate(BaseModel):
    name: str = ""               # 名称：如 店里 / 工厂 / 仓库
    sender_name: str = ""        # 发件人姓名
    phone: str = ""              # 电话
    address: str = ""            # 地址
    remark: str = ""             # 备注（可空）


class SenderOut(SenderCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- 标签打印布局模板（跟随登录账号） ----------
class LabelTemplateCreate(BaseModel):
    name: str                                  # 模板名
    type: str = "goods"                        # goods=商品标签 / logistics=物流面单
    data: str = "{}"                           # 布局配置 JSON 字符串
    is_default: bool = False                   # 同类型是否默认模板


class LabelTemplateUpdate(BaseModel):
    name: str | None = None
    data: str | None = None
    is_default: bool | None = None


class LabelTemplateOut(BaseModel):
    id: int
    user_id: int
    name: str
    type: str
    data: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- 设置中心 ----------
class PreferenceOut(BaseModel):
    theme: str = "light"            # light=亮 / dark=暗 / random=随机
    theme_color: str = "default"    # 预设主题 key
    bg_image: str = ""              # 背景图文件名（空=无）


class PreferenceUpdate(BaseModel):
    theme: str = "light"
    theme_color: str = "default"
    bg_image: str = ""


class MigrateRequest(BaseModel):
    new_dir: str                    # 目标数据目录绝对路径


class StorageOut(BaseModel):
    data_dir: str
    db_path: str
    media_dir: str
    db_size: int

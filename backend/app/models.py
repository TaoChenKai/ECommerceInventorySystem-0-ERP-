from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    """账号：boss=老板(超管) / admin=管理员 / staff=员工"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(64), default="")
    role = Column(String(16), default="staff")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPreference(Base):
    """用户个性化偏好（设置中心），一个用户一行；换设备登录一致。
    theme: light=亮 / dark=暗 / random=随机（明暗分组）
    theme_color: 预设主题 key（default/day/night/mint/sun/violet）
    bg_image: 背景图文件名（存 MEDIA_DIR，可空）
    """
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    theme = Column(String(16), default="light")
    theme_color = Column(String(32), default="default")
    bg_image = Column(String(255), default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User")


class Category(Base):
    """商品分类"""
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)
    remark = Column(String(255), default="")


class Spu(Base):
    """商品款式（SPU），如：T恤·纯棉款"""
    __tablename__ = "spus"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    code = Column(String(64), index=True)          # 商品编号（可空，应用层校验唯一）
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    unit = Column(String(16), default="件")        # 计数单位（件/个/箱/盒...，取自单位字典，可自定义）
    weight = Column(Float, default=0)
    weight_unit = Column(String(16), default="千克")  # 重量单位（克/千克/吨...，取自重量单位字典，可自定义）
    designer = Column(String(128), default="")     # 设计者（标签打印 / 商品详情展示）
    production_date = Column(Date, nullable=True)  # 生产日期
    material = Column(String(128), default="")     # 材质（标签打印 / 商品详情展示）
    image_url = Column(String(255), default="")    # 旧版单图URL（兼容保留），新版统一走 product_images
    remark = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)   # 软删除：NULL=正常，非NULL=已进回收站
    category = relationship("Category")
    skus = relationship("Sku", back_populates="spu", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="spu",
                          cascade="all, delete-orphan", order_by="ProductImage.sort")


class ProductImage(Base):
    """商品图片：img_type = main(美工图/主图) / detail(详情介绍图)，张数不限，可自由排序"""
    __tablename__ = "product_images"
    id = Column(Integer, primary_key=True, index=True)
    spu_id = Column(Integer, ForeignKey("spus.id"), nullable=False)
    img_type = Column(String(16), default="main")
    url = Column(String(255), nullable=False)
    sort = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    spu = relationship("Spu", back_populates="images")


class Unit(Base):
    """计数单位字典：件/个/箱/盒/套/只/包/张/台...，用户可在商品页内随时增删改"""
    __tablename__ = "units"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(16), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class WeightUnit(Base):
    """重量单位字典：克/千克/吨/斤/磅...，用户可随时增删改"""
    __tablename__ = "weight_units"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(16), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Sku(Base):
    """具体规格（SKU），如：红色XL"""
    __tablename__ = "skus"
    id = Column(Integer, primary_key=True, index=True)
    spu_id = Column(Integer, ForeignKey("spus.id"), nullable=False)
    spec_name = Column(String(128), default="")                 # 规格名，如 红色/XL
    sku_code = Column(String(64), index=True)
    barcode = Column(String(64), index=True)                    # 条码
    cost_price = Column(Float, default=0)                       # 进价
    sale_price = Column(Float, default=0)                       # 售价
    stock = Column(Integer, default=0)                          # 当前库存
    created_at = Column(DateTime, default=datetime.utcnow)
    spu = relationship("Spu", back_populates="skus")


class Channel(Base):
    """销售渠道（实体店 / 天猫 / 淘宝 / 拼多多 / 京东 / 抖音 / 海外等，可自定义）"""
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)
    channel_type = Column(String(32), default="platform")       # store=实体店 / platform=电商平台 / other
    remark = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class StockLog(Base):
    """出入库流水，逐笔可追溯，记录渠道来源"""
    __tablename__ = "stock_logs"
    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    log_type = Column(String(16))                               # in=入库 / out=出库
    quantity = Column(Integer, default=0)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    remark = Column(String(255), default="")                   # 备注，如 618补货 / 打包发货
    created_at = Column(DateTime, default=datetime.utcnow)
    sku = relationship("Sku")
    channel = relationship("Channel")
    operator = relationship("User", foreign_keys=[operator_id])


class Supplier(Base):
    """供应商 / 采购商"""
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False)
    contact = Column(String(64), default="")          # 联系人
    phone = Column(String(32), default="")
    remark = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class PurchaseOrder(Base):
    """采购单：供应商 + 采购方式 + 明细，草稿可增删，确认后统一建档入库"""
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(32), unique=True, nullable=False)  # 单号 P20260821-001
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    purchase_method = Column(String(32), default="")  # 采购方式：现款现货/赊账/月结/代销...
    order_date = Column(String(16), default="")       # 采购日期 YYYY-MM-DD
    remark = Column(String(255), default="")
    status = Column(String(16), default="draft")      # draft=草稿 / done=已入库 / cancelled=已取消
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    supplier = relationship("Supplier")
    operator = relationship("User", foreign_keys=[operator_id])
    items = relationship("PurchaseItem", back_populates="order",
                         cascade="all, delete-orphan", order_by="PurchaseItem.id")


class PurchaseItem(Base):
    """采购明细：已建档商品直接引用SKU；未建档商品存草稿字段，确认入库时统一建档"""
    __tablename__ = "purchase_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    spu_id = Column(Integer, ForeignKey("spus.id"), nullable=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=True)
    status = Column(String(16), default="existing")   # existing=已建档 / draft=待建档
    quantity = Column(Integer, default=1)             # 本次采购数量
    unit_price = Column(Float, default=0)             # 本次采购单价
    # ---- 待建档商品草稿字段（仅 status=draft 时使用）----
    draft_name = Column(String(128), default="")
    draft_code = Column(String(64), default="")
    draft_spec = Column(String(128), default="")
    draft_barcode = Column(String(64), default="")
    draft_category = Column(String(64), default="")
    draft_unit = Column(String(16), default="件")
    draft_weight = Column(Float, default=0)
    draft_weight_unit = Column(String(16), default="千克")
    draft_remark = Column(Text, default="")
    draft_images = Column(Text, default="")           # JSON 字符串：["url1","url2",...]
    created_at = Column(DateTime, default=datetime.utcnow)
    order = relationship("PurchaseOrder", back_populates="items")
    sku = relationship("Sku")


class SaleOrder(Base):
    """销售出库单：渠道 + 买家 + 明细，草稿可增删改，确认出库后减库存留档
    预留开票 / 打回单扩展字段：invoice_no / invoice_status / receipt_no
    """
    __tablename__ = "sale_orders"
    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(32), unique=True, nullable=False)  # 单号 S20260821-001
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    buyer = Column(String(128), default="")                     # 客户/买家，可留空
    remark = Column(String(255), default="")
    status = Column(String(16), default="draft")                # draft=草稿 / done=已完成 / cancelled=已取消
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    # ---- 预留：开票 / 打回单 ----
    invoice_no = Column(String(64), default="")                 # 发票号
    invoice_status = Column(String(16), default="uninvoiced")   # uninvoiced=未开票 / invoiced=已开票 / void=作废
    receipt_no = Column(String(64), default="")                 # 回单号
    created_at = Column(DateTime, default=datetime.utcnow)
    channel = relationship("Channel")
    operator = relationship("User", foreign_keys=[operator_id])
    items = relationship("SaleItem", back_populates="order",
                         cascade="all, delete-orphan", order_by="SaleItem.id")


class SaleItem(Base):
    """销售明细：实际销售单价 + 折扣系数随行保存，小计 = 数量 × 单价"""
    __tablename__ = "sale_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("sale_orders.id"), nullable=False)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    quantity = Column(Integer, default=1)       # 销售数量
    discount = Column(Float, default=0)         # 折扣系数：0=无折扣，0.35=3.5折
    unit_price = Column(Float, default=0)       # 实际销售单价
    cost_price = Column(Float, nullable=True)   # 成本价快照（确认出库时写入，保证历史对账不随档案成本漂移；旧单为空时统计回退取当前 SKU 成本）
    created_at = Column(DateTime, default=datetime.utcnow)
    order = relationship("SaleOrder", back_populates="items")
    sku = relationship("Sku")


class SenderProfile(Base):
    """常用发件人档案（可多个，物流标签打印时快速调用）"""
    __tablename__ = "senders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), default="")          # 名称：如 店里 / 工厂 / 仓库
    sender_name = Column(String(64), default="")   # 发件人姓名
    phone = Column(String(32), default="")         # 电话
    address = Column(String(255), default="")      # 地址
    remark = Column(String(255), default="")       # 备注（可空）
    created_at = Column(DateTime, default=datetime.utcnow)


class LabelTemplate(Base):
    """标签打印布局模板（跟随登录账号隔离，跨设备云端一致）"""
    __tablename__ = "label_templates"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 账号隔离
    name = Column(String(64), nullable=False)          # 模板名
    type = Column(String(16), nullable=False)          # goods=商品标签 / logistics=物流面单
    data = Column(Text, default="{}")                  # 布局配置 JSON 字符串
    is_default = Column(Boolean, default=False)        # 同类型是否默认模板
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User")


class AuditLog(Base):
    """操作日志"""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(64), default="")
    action = Column(String(255))
    detail = Column(Text, default="")
    ip = Column(String(64), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

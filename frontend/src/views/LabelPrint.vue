<template>
  <!-- 屏幕 UI（打印时整块隐藏） -->
  <div class="lbl-screen">
    <h2>标签打印</h2>
    <p class="desc">商品标签（热敏小票机）+ 物流标签（快递面单），预览所见即所得，点「立即打印」直接出纸</p>

    <div class="lbl-tabs">
      <button :class="{ active: activeTab === 'goods' }" @click="switchTab('goods')">商品标签</button>
      <button :class="{ active: activeTab === 'logistics' }" @click="switchTab('logistics')">物流标签</button>
    </div>

    <!-- 打印机偏好设置（存 localStorage，打印时智能提示） -->
    <div class="panel printer-pref">
      <div class="pref-title">打印机偏好（保存后打印前智能提示，可留空）</div>
      <div class="pref-row">
        <div class="fitem">
          <label>商品标签打印机（热敏小票机）</label>
          <input v-model="goodsPrinter" placeholder="如：乐名 / TSC" @change="savePrinterPref" />
        </div>
        <div class="fitem">
          <label>物流面单打印机（大打印机）</label>
          <input v-model="logiPrinter" placeholder="如：得力 / 佳博" @change="savePrinterPref" />
        </div>
      </div>
    </div>

    <!-- ================= 页签A：商品标签 ================= -->
    <div v-show="activeTab === 'goods'" class="panel">
      <div class="lbl-grid">
        <div class="fitem">
          <label>选择商品（名称 / 编号搜索）</label>
          <div class="unit-row">
            <input v-model="spuKeyword" placeholder="输入名称或编号搜索" @keyup.enter="searchSpus" />
            <button @click="searchSpus">搜索</button>
          </div>
          <select v-model="selectedSpuId" style="margin-top: 8px" @change="onSpuChange">
            <option :value="null" disabled>— 选择商品 —</option>
            <option v-for="s in spuOptions" :key="s.id" :value="s.id">{{ s.name }}{{ s.code ? `（${s.code}）` : '' }}</option>
          </select>
          <select v-model="selectedSkuId" style="margin-top: 8px" :disabled="!skuOptions.length">
            <option :value="null" disabled>— 选择规格 —</option>
            <option v-for="k in skuOptions" :key="k.id" :value="k.id">{{ k.spec_name || '默认' }}（{{ k.sku_code || '无编码' }}）¥{{ k.sale_price }}</option>
          </select>
          <div style="margin-top: 8px">
            <button :disabled="!selectedSkuId" @click="addToQueue">+ 加入打印队列</button>
          </div>
        </div>

        <div class="fitem">
          <label>标签纸尺寸（打印区 mm 宽×高）</label>
          <div class="unit-row">
            <select v-model="goodsSizeIndex">
              <option v-for="(sz, i) in GOODS_SIZES" :key="i" :value="i">{{ sz.label }}</option>
            </select>
            <template v-if="isCustomGoods">
              <input v-model.number="goodsCustomW" type="number" min="10" placeholder="宽mm" style="width: 70px" />
              <span>×</span>
              <input v-model.number="goodsCustomH" type="number" min="10" placeholder="高mm" style="width: 70px" />
            </template>
          </div>
        </div>

        <div class="fitem compat-box" style="grid-column: 1 / -1">
          <label>
            <input type="checkbox" v-model="goodsFitPrintable" style="width: auto; height: auto; margin-right: 6px" />
            热敏打印机兼容（自动收进打印头可打印宽度）
          </label>
          <div class="unit-row" style="font-size: 12px">
            <span class="muted">打印头有效宽</span>
            <input v-model.number="goodsPrintableW" type="number" min="10" max="100" style="width: 70px; height: 32px" />
            <span class="muted">mm（佳博 GP-2120TUA 约 48mm，60mm 纸两侧各约 6mm 打不出）</span>
          </div>
          <div v-if="goodsSafePadMm > 0" class="muted" style="font-size: 12px; line-height: 1.6">
            当前标签宽 {{ goodsSize.w }}mm，内容将自动居中收进中间 {{ goodsPrintableW }}mm 可打印区，左右各留 {{ goodsSafePadMm }}mm 白边。
          </div>
        </div>

        <div class="fitem" style="grid-column: 1 / -1">
          <label>打印内容模式</label>
          <div class="mode-btn-row">
            <button class="mode-btn" :class="{ active: goodsModeState === 'barcode' }" @click="setGoodsMode('barcode')">仅一维码</button>
            <button class="mode-btn" :class="{ active: goodsModeState === 'qrcode' }" @click="setGoodsMode('qrcode')">仅二维码</button>
            <button class="mode-btn" :class="{ active: goodsModeState === 'both' }" @click="setGoodsMode('both')">一维码 + 二维码</button>
          </div>
          <div style="display: flex; align-items: center; gap: 10px; margin-top: 8px; flex-wrap: wrap">
            <button class="mini-btn" @click="autoLayoutGoods">自动排版（条码 / 价格 / 名称三段居中）</button>
            <span class="muted" style="font-size: 12px">一键重排：上条码、中价格、下名称，整组垂直居中，宽度适配可打印区</span>
          </div>
          <div class="muted" style="font-size: 12px; line-height: 1.6">切换后实时同步预览与打印内容</div>
        </div>

        <div class="fitem" style="grid-column: 1 / -1">
          <div class="layout-toggle" @click="toggleLayoutEditor">
            <span class="layout-toggle-title">布局设置（拖拽 + 数值面板 DIY）</span>
            <span class="layout-toggle-arrow">{{ layoutExpanded ? '收起 ▲' : '展开 ▼' }}</span>
          </div>
          <div class="muted" style="font-size: 12px; line-height: 1.6">
            拖动元素调整位置，拖右下角调整宽度；商品标签元素：一维码 / 二维码 / 产品名称 / 价格。布局可保存为云端模板跟随账号。
          </div>
          <!-- 内嵌布局编辑器（随页签切换显示对应布局） -->
          <div v-show="layoutExpanded" class="layout-embed">
            <div class="layout-main">
              <div class="layout-canvas-wrap">
                <div ref="goodsCanvasEl" class="layout-canvas" :style="{ width: curSize.w + 'mm', height: curSize.h + 'mm' }">
                  <!-- 商品标签画布：真实渲染条码/二维码/名称/价格（数据=队列第一项或当前选中商品） -->
                  <!-- 热敏打印头兼容安全区（佳博 GP-2120TUA 打印头有效宽约 48mm）：灰底区为打印头打不到的左右边距，元素应居中放在中间可打印区 -->
                  <div v-if="layoutType === 'goods' && goodsSafePadMm > 0" class="printable-guide" :style="{ left: goodsSafePadMm + 'mm', right: goodsSafePadMm + 'mm' }">
                    <span class="printable-guide-tag">可打印区（打印头有效宽 {{ goodsPrintableW }}mm）</span>
                  </div>
                  <template v-if="layoutType === 'goods'">
                    <div class="print-safe" :style="printSafeStyle">
                      <div
                        v-for="el in curLayout"
                        :key="el.id"
                        class="layout-el real"
                        :class="{ active: selectedElId === el.id, hidden: !el.visible }"
                        :style="elBoxStyle(el)"
                        @mousedown="startDrag($event, el)"
                      >
                        <template v-if="canvasDemo">
                          <img v-if="el.id === 'barcode' && canvasDemo.barcodeUrl" :src="canvasDemo.barcodeUrl" class="diy-barcode-img" :style="barcodeImgStyle(el)" />
                          <div v-if="el.id === 'barcode'" class="diy-barcode-text" :style="elTextStyle(el)">{{ canvasDemo.sku.sku_code || canvasDemo.sku.barcode }}</div>
                          <img v-else-if="el.id === 'qrcode' && canvasDemo.qrUrl" :src="canvasDemo.qrUrl" class="diy-qrcode-img" :style="qrImgStyle(el)" />
                          <div v-else-if="el.id === 'name'" class="diy-text" :style="elTextStyle(el)">{{ canvasDemo.spu.name }}</div>
                          <div v-else-if="el.id === 'price'" class="diy-text diy-price" :style="elTextStyle(el)">{{ priceText(canvasDemo) }}</div>
                        </template>
                        <span v-else class="layout-el-label">{{ el.name }}</span>
                        <span class="layout-el-name">{{ el.name }}</span>
                        <span class="layout-el-resize" @mousedown="startResize($event, el)"></span>
                      </div>
                    </div>
                  </template>
                  <!-- 物流面单画布：真实渲染表单数据 -->
                  <template v-else>
                    <div
                      v-for="el in curLayout"
                      :key="el.id"
                      class="layout-el real"
                      :class="{ active: selectedElId === el.id, hidden: !el.visible }"
                      :style="elBoxStyle(el)"
                      @mousedown="startDrag($event, el)"
                    >
                      <div v-if="el.id === 'company'" class="diy-text diy-company" :style="elTextStyle(el)">{{ logi.company || '快递公司' }}</div>
                      <div v-else-if="el.id === 'track'" class="diy-text diy-track" :style="elTextStyle(el)">{{ logi.track_no }}</div>
                      <div v-else-if="el.id === 'recv'" class="diy-text" :style="elTextStyle(el)">
                        <div>收件人：{{ logi.recv_name || '' }} {{ logi.recv_phone || '' }}</div>
                        <div>{{ logi.recv_addr }}</div>
                      </div>
                      <div v-else-if="el.id === 'send'" class="diy-text" :style="elTextStyle(el)">
                        <div>发件人：{{ currentSender?.sender_name || '' }} {{ currentSender?.phone || '' }}</div>
                        <div>{{ currentSender?.address || '' }}</div>
                      </div>
                      <div v-else-if="el.id === 'remark'" class="diy-text diy-remark" :style="elTextStyle(el)">备注：{{ logi.remark }}</div>
                      <span class="layout-el-name">{{ el.name }}</span>
                      <span class="layout-el-resize" @mousedown="startResize($event, el)"></span>
                    </div>
                  </template>
                  <div v-if="layoutType === 'goods' && !canvasDemo" class="layout-canvas-tip">选择商品或加入打印队列后，此处实时显示该商品的真实打印效果（条码 / 名称 / 价格）</div>
                </div>
                <div class="muted" style="margin-top: 6px">画布 1:1（{{ curSize.w }}mm × {{ curSize.h }}mm），拖动元素调位置，拖右下角调宽度</div>
              </div>
              <div class="layout-panel">
                <div class="lp-el-list">
                  <span
                    v-for="el in curLayout"
                    :key="el.id"
                    class="lp-el-chip"
                    :class="{ on: selectedElId === el.id, off: !el.visible }"
                    @click="selectedElId = el.id"
                  >{{ el.name }}{{ el.visible ? '' : '（隐藏）' }}</span>
                </div>
                <template v-if="selectedEl">
                  <div class="lp-title">元素：{{ selectedEl.name }}</div>
                  <div class="lp-row"><label>显示</label><input type="checkbox" v-model="selectedEl.visible" /></div>
                  <div class="lp-row">
                    <label>水平对齐</label>
                    <select v-model="selectedEl.align">
                      <option value="left">左</option><option value="center">中</option><option value="right">右</option>
                    </select>
                  </div>
                  <div class="lp-row"><label>左边距 (mm)</label><input type="number" min="0" step="0.5" v-model.number="selectedEl.left" /></div>
                  <div class="lp-row"><label>顶部位置 (mm)</label><input type="number" min="0" step="0.5" v-model.number="selectedEl.top" /></div>
                  <div class="lp-row"><label>宽度 (mm)</label><input type="number" min="4" step="0.5" v-model.number="selectedEl.width" /></div>
                  <div class="lp-row"><label>字号 (mm)</label><input type="number" min="0.5" step="0.1" v-model.number="selectedEl.fontSizeMm" /></div>
                  <div class="lp-row">
                    <label>整体缩放</label>
                    <input type="range" min="0.1" max="2" step="0.05" v-model.number="selectedEl.scale" style="flex: 1; min-width: 0" />
                    <span class="lp-scale-val">{{ Math.round((selectedEl.scale || 1) * 100) }}%</span>
                    <button class="mini-btn" style="height: 28px; padding: 0 8px" @click="selectedEl.scale = 1">复原</button>
                  </div>
                  <div class="lp-row">
                    <label>字体</label>
                    <select v-model="selectedEl.fontFamily">
                      <option v-for="f in FONT_LIST" :key="f" :value="f">{{ fontLabel(f) }}</option>
                    </select>
                  </div>
                  <div class="lp-row lp-check-group">
                    <label><input type="checkbox" v-model="selectedEl.bold" /> 加粗</label>
                    <label><input type="checkbox" v-model="selectedEl.italic" /> 斜体</label>
                    <label><input type="checkbox" v-model="selectedEl.underline" /> 下划线</label>
                  </div>
                </template>
                <div v-else class="muted">点击画布中的元素或上方元素列表进行编辑</div>
                <div class="lp-divider"></div>
                <div class="lp-title">模板管理</div>
                <div class="lp-tpl-list">
                  <div v-for="tpl in templates" :key="tpl.id" class="lp-tpl-item">
                    <span class="lp-tpl-name" :class="{ 'is-default': tpl.is_default }" @click="applyTemplate(tpl)">{{ tpl.name }}{{ tpl.is_default ? '（默认）' : '' }}</span>
                    <button class="mini-btn" @click="renameTemplate(tpl)">重命名</button>
                    <button class="mini-btn danger" @click="removeTemplate(tpl)">删除</button>
                  </div>
                  <div v-if="!templates.length" class="muted">暂无模板</div>
                </div>
                <div class="lp-actions">
                  <button class="mini-btn" @click="saveAsNamedTemplate">保存为新模板</button>
                  <button class="pc-go lp-save-default" @click="saveAsDefaultTemplate">保存为默认模板</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div style="display: flex; align-items: center; margin-top: 16px">
        <b>打印队列（{{ goodsQueue.length }}）</b>
        <span style="flex: 1"></span>
        <button v-if="goodsQueue.length" class="mini-btn danger" @click="goodsQueue = []">清空队列</button>
      </div>
      <div v-if="goodsQueue.length" class="queue-list">
        <span v-for="(it, i) in goodsQueue" :key="i" class="tag">
          {{ it.spu.name }} · {{ it.sku.spec_name || '默认' }}
          <a style="margin-left: 6px; cursor: pointer" @click="goodsQueue.splice(i, 1)">×</a>
        </span>
      </div>
      <div v-else class="muted" style="margin-top: 8px">队列为空，先搜索并选择商品规格加入队列。</div>

      <!-- 商品预览 / 打印区 -->
      <div class="preview-wrap" v-if="goodsQueue.length">
        <div class="muted" style="margin-bottom: 8px">预览（{{ goodsSize.w }}mm × {{ goodsSize.h }}mm，1:1）</div>
        <div class="preview-sheet">
          <div
            v-for="(it, i) in goodsQueue"
            :key="i"
            class="goods-card"
            :style="goodsCardStyle"
          >
            <div class="print-safe" :style="printSafeStyle">
              <div
                v-for="el in goodsLayout"
                :key="el.id"
                v-show="el.visible"
                class="diy-el"
                :style="elBoxStyle(el)"
              >
                <img v-if="el.id === 'barcode' && it.barcodeUrl" :src="it.barcodeUrl" class="diy-barcode-img" :style="barcodeImgStyle(el)" />
                <div v-if="el.id === 'barcode'" class="diy-barcode-text" :style="elTextStyle(el)">{{ it.sku.sku_code || it.sku.barcode }}</div>
                <img v-else-if="el.id === 'qrcode' && it.qrUrl" :src="it.qrUrl" class="diy-qrcode-img" :style="qrImgStyle(el)" />
                <div v-else-if="el.id === 'name'" class="diy-text" :style="elTextStyle(el)">{{ it.spu.name }}</div>
                <div v-else-if="el.id === 'price'" class="diy-text diy-price" :style="elTextStyle(el)">{{ priceText(it) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="goodsQueue.length" style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px">
        <button class="btn-print" @click="openPrintModal('goods')">立即打印（{{ goodsSize.w }}×{{ goodsSize.h }}mm）</button>
      </div>
    </div>

    <!-- ================= 页签B：物流标签 ================= -->
    <div v-show="activeTab === 'logistics'" class="panel">
      <div class="lbl-grid">
        <div class="fitem">
          <label>快递公司</label>
          <input v-model="logi.company" list="company-options" placeholder="如：顺丰 / 中通 / 韵达 / 圆通 / 自定义" />
          <datalist id="company-options">
            <option value="顺丰速运" /><option value="中通快递" /><option value="韵达快递" /><option value="圆通速递" /><option value="申通快递" /><option value="极兔速递" /><option value="京东物流" /><option value="邮政EMS" />
          </datalist>
        </div>
        <div class="fitem">
          <label>快递单号（可空）</label>
          <input v-model="logi.track_no" placeholder="运单号，可留空" />
        </div>
        <div class="fitem">
          <label>收件人姓名</label>
          <input v-model="logi.recv_name" placeholder="收件人" />
        </div>
        <div class="fitem">
          <label>收件人电话</label>
          <input v-model="logi.recv_phone" placeholder="手机 / 固话" />
        </div>
        <div class="fitem" style="grid-column: 1 / -1">
          <label>收件人地址</label>
          <input v-model="logi.recv_addr" placeholder="省市区 + 详细地址" />
        </div>
        <div class="fitem">
          <label>发件人</label>
          <div class="unit-row">
            <select v-model="logi.sender_id">
              <option :value="null" disabled>— 选择常用发件人 —</option>
              <option v-for="s in senders" :key="s.id" :value="s.id">{{ s.name }}({{ s.sender_name }})</option>
            </select>
            <button class="mini-btn" @click="showSenderModal = true">新增发件人</button>
          </div>
          <div v-if="currentSender" class="sender-preview">
            <div>发件人：{{ currentSender.sender_name }} {{ currentSender.phone }}</div>
            <div>地址：{{ currentSender.address }}</div>
          </div>
        </div>
        <div class="fitem">
          <label>备注（可空）</label>
          <input v-model="logi.remark" placeholder="如：易碎品 / 生鲜 / 货到付款" />
        </div>
        <div class="fitem" style="grid-column: 1 / -1">
          <label>面单尺寸（mm 宽×高）</label>
          <div class="unit-row">
            <select v-model="logiSizeIndex">
              <option v-for="(sz, i) in LOGI_SIZES" :key="i" :value="i">{{ sz.label }}</option>
            </select>
            <template v-if="isCustomLogi">
              <input v-model.number="logiCustomW" type="number" min="30" placeholder="宽mm" style="width: 70px" />
              <span>×</span>
              <input v-model.number="logiCustomH" type="number" min="30" placeholder="高mm" style="width: 70px" />
            </template>
          </div>
        </div>
        <div class="fitem" style="grid-column: 1 / -1">
          <div class="layout-toggle" @click="toggleLayoutEditor">
            <span class="layout-toggle-title">布局设置（拖拽 + 数值面板 DIY）</span>
            <span class="layout-toggle-arrow">{{ layoutExpanded ? '收起 ▲' : '展开 ▼' }}</span>
          </div>
          <div class="muted" style="font-size: 12px; line-height: 1.6">
            拖动元素调整位置，拖右下角调整宽度；物流面单元素：快递公司 / 单号 / 收件人区 / 发件人区 / 备注。布局可保存为云端模板跟随账号。
          </div>
          <!-- 内嵌布局编辑器（随页签切换显示对应布局） -->
          <div v-show="layoutExpanded" class="layout-embed">
            <div class="layout-main">
              <div class="layout-canvas-wrap">
                <div ref="logiCanvasEl" class="layout-canvas" :style="{ width: curSize.w + 'mm', height: curSize.h + 'mm' }">
                  <div
                    v-for="el in curLayout"
                    :key="el.id"
                    class="layout-el"
                    :class="{ active: selectedElId === el.id, hidden: !el.visible }"
                    :style="elBoxStyle(el)"
                    @mousedown="startDrag($event, el)"
                  >
                    <span class="layout-el-label">{{ el.name }}</span>
                    <span class="layout-el-resize" @mousedown="startResize($event, el)"></span>
                  </div>
                </div>
                <div class="muted" style="margin-top: 6px">画布 1:1（{{ curSize.w }}mm × {{ curSize.h }}mm），拖动元素调位置，拖右下角调宽度</div>
              </div>
              <div class="layout-panel">
                <div class="lp-el-list">
                  <span
                    v-for="el in curLayout"
                    :key="el.id"
                    class="lp-el-chip"
                    :class="{ on: selectedElId === el.id, off: !el.visible }"
                    @click="selectedElId = el.id"
                  >{{ el.name }}{{ el.visible ? '' : '（隐藏）' }}</span>
                </div>
                <template v-if="selectedEl">
                  <div class="lp-title">元素：{{ selectedEl.name }}</div>
                  <div class="lp-row"><label>显示</label><input type="checkbox" v-model="selectedEl.visible" /></div>
                  <div class="lp-row">
                    <label>水平对齐</label>
                    <select v-model="selectedEl.align">
                      <option value="left">左</option><option value="center">中</option><option value="right">右</option>
                    </select>
                  </div>
                  <div class="lp-row"><label>左边距 (mm)</label><input type="number" min="0" step="0.5" v-model.number="selectedEl.left" /></div>
                  <div class="lp-row"><label>顶部位置 (mm)</label><input type="number" min="0" step="0.5" v-model.number="selectedEl.top" /></div>
                  <div class="lp-row"><label>宽度 (mm)</label><input type="number" min="4" step="0.5" v-model.number="selectedEl.width" /></div>
                  <div class="lp-row"><label>字号 (mm)</label><input type="number" min="0.5" step="0.1" v-model.number="selectedEl.fontSizeMm" /></div>
                  <div class="lp-row">
                    <label>整体缩放</label>
                    <input type="range" min="0.1" max="2" step="0.05" v-model.number="selectedEl.scale" style="flex: 1; min-width: 0" />
                    <span class="lp-scale-val">{{ Math.round((selectedEl.scale || 1) * 100) }}%</span>
                    <button class="mini-btn" style="height: 28px; padding: 0 8px" @click="selectedEl.scale = 1">复原</button>
                  </div>
                  <div class="lp-row">
                    <label>字体</label>
                    <select v-model="selectedEl.fontFamily">
                      <option v-for="f in FONT_LIST" :key="f" :value="f">{{ fontLabel(f) }}</option>
                    </select>
                  </div>
                  <div class="lp-row lp-check-group">
                    <label><input type="checkbox" v-model="selectedEl.bold" /> 加粗</label>
                    <label><input type="checkbox" v-model="selectedEl.italic" /> 斜体</label>
                    <label><input type="checkbox" v-model="selectedEl.underline" /> 下划线</label>
                  </div>
                </template>
                <div v-else class="muted">点击画布中的元素或上方元素列表进行编辑</div>
                <div class="lp-divider"></div>
                <div class="lp-title">模板管理</div>
                <div class="lp-tpl-list">
                  <div v-for="tpl in templates" :key="tpl.id" class="lp-tpl-item">
                    <span class="lp-tpl-name" :class="{ 'is-default': tpl.is_default }" @click="applyTemplate(tpl)">{{ tpl.name }}{{ tpl.is_default ? '（默认）' : '' }}</span>
                    <button class="mini-btn" @click="renameTemplate(tpl)">重命名</button>
                    <button class="mini-btn danger" @click="removeTemplate(tpl)">删除</button>
                  </div>
                  <div v-if="!templates.length" class="muted">暂无模板</div>
                </div>
                <div class="lp-actions">
                  <button class="mini-btn" @click="saveAsNamedTemplate">保存为新模板</button>
                  <button class="pc-go lp-save-default" @click="saveAsDefaultTemplate">保存为默认模板</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 物流预览 / 打印区 -->
      <div class="preview-wrap" style="margin-top: 16px">
        <div class="muted" style="margin-bottom: 8px">预览（{{ logiSize.w }}mm × {{ logiSize.h }}mm，1:1）</div>
        <div class="preview-sheet">
          <div class="logi-card" :style="logiCardStyle">
            <div
              v-for="el in logiLayout"
              :key="el.id"
              v-show="el.visible"
              class="diy-el"
              :style="elBoxStyle(el)"
            >
              <div v-if="el.id === 'company'" class="diy-text diy-company" :style="elTextStyle(el)">{{ logi.company || '快递公司' }}</div>
              <div v-else-if="el.id === 'track'" class="diy-text diy-track" :style="elTextStyle(el)">{{ logi.track_no }}</div>
              <div v-else-if="el.id === 'recv'" class="diy-text" :style="elTextStyle(el)">
                <div>收件人：{{ logi.recv_name || '' }} {{ logi.recv_phone || '' }}</div>
                <div>{{ logi.recv_addr }}</div>
              </div>
              <div v-else-if="el.id === 'send'" class="diy-text" :style="elTextStyle(el)">
                <div>发件人：{{ currentSender?.sender_name || '' }} {{ currentSender?.phone || '' }}</div>
                <div>{{ currentSender?.address || '' }}</div>
              </div>
              <div v-else-if="el.id === 'remark'" class="diy-text diy-remark" :style="elTextStyle(el)">备注：{{ logi.remark }}</div>
            </div>
          </div>
        </div>
      </div>

      <div style="display: flex; justify-content: flex-end; margin-top: 18px">
        <button class="btn-print" @click="openPrintModal('logistics')">立即打印（{{ logiSize.w }}×{{ logiSize.h }}mm）</button>
      </div>
    </div>

    <!-- 新增发件人弹窗 -->
    <div v-if="showSenderModal" class="modal-mask" @click.self="showSenderModal = false">
      <div class="modal">
        <h3>新增常用发件人</h3>
        <div class="modal-form">
          <div class="fitem"><label>名称 *（如：店里 / 工厂 / 仓库）</label><input v-model="senderForm.name" placeholder="自定义名称" /></div>
          <div class="fitem"><label>发件人姓名 *</label><input v-model="senderForm.sender_name" /></div>
          <div class="fitem"><label>电话</label><input v-model="senderForm.phone" /></div>
          <div class="fitem"><label>地址</label><input v-model="senderForm.address" /></div>
          <div class="fitem"><label>备注（可空）</label><input v-model="senderForm.remark" /></div>
        </div>
        <div class="modal-actions">
          <button class="btn-plain" @click="showSenderModal = false">取消</button>
          <button @click="saveSender">保存</button>
        </div>
      </div>
    </div>

    <!-- 打印确认弹窗 -->
    <div v-if="showPrintModal" class="modal-mask" @click.self="showPrintModal = false">
      <div class="modal print-confirm">
        <h3>确认打印</h3>
        <div class="pc-type">{{ printCtx.title }}</div>
        <div class="pc-size">标签尺寸：{{ printCtx.size }}</div>
        <div class="pc-printer">
          <template v-if="printCtx.printer">
            推荐打印机：<b class="pc-name">{{ printCtx.printer }}</b>
          </template>
          <template v-else>
            未设置打印机偏好，请在系统打印窗口手动选择对应打印机（{{ printCtx.hint }}）
          </template>
        </div>
        <div class="muted" style="line-height: 1.7">
          点击「继续打印」后将弹出系统打印窗口，请确认打印机与纸张尺寸（{{ printCtx.size }}）无误后再打印。
        </div>
        <div v-if="printCtx.compatPad > 0" class="pc-compat">
          <div class="pc-compat-title">热敏打印头兼容已开启（左右各留 {{ printCtx.compatPad }}mm 白边，内容居中收进中间 {{ printCtx.printableW }}mm 可打印区）</div>
          <div class="pc-compat-steps">
            <div>1. 系统打印窗口：纸张务必选「60×40」（宽 60mm 高 40mm）或与标签一致的纸型</div>
            <div>2. 方向务必保持「横向」（标签纸横放槽内），勿切「纵向」——切纵向会使纸型尺寸反转成 40×60，导致内容超格、方向错乱</div>
            <div>3. 缩放设为「100%」，边距选「无」，关闭页眉页脚</div>
            <div>4. 若打印窗口没有 60×40 纸型：打印机首选项 → 自定义纸张新建「60x40」（宽 60mm 高 40mm）并设为默认，纸张类型选「间隙纸」</div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-plain" @click="showPrintModal = false">取消</button>
          <button class="pc-go" @click="doPrint">继续打印</button>
        </div>
      </div>
    </div>

  </div>

  <!-- 商品打印区（Teleport 到 body 直接子级，打印时仅此处显示，避免撑出多页） -->
  <Teleport to="body">
    <div id="goods-print-area" class="print-area" v-if="goodsQueue.length">
      <div
        v-for="(it, i) in goodsQueue"
        :key="i"
        class="goods-card print-card"
        :style="goodsCardStyle"
      >
        <div class="print-safe" :style="printSafeStyle">
          <div
            v-for="el in goodsLayout"
            :key="el.id"
            v-show="el.visible"
            class="diy-el"
            :style="elBoxStyle(el)"
          >
            <img v-if="el.id === 'barcode' && it.barcodeUrl" :src="it.barcodeUrl" class="diy-barcode-img" :style="barcodeImgStyle(el)" />
            <div v-if="el.id === 'barcode'" class="diy-barcode-text" :style="elTextStyle(el)">{{ it.sku.sku_code || it.sku.barcode }}</div>
            <img v-else-if="el.id === 'qrcode' && it.qrUrl" :src="it.qrUrl" class="diy-qrcode-img" :style="qrImgStyle(el)" />
            <div v-else-if="el.id === 'name'" class="diy-text" :style="elTextStyle(el)">{{ it.spu.name }}</div>
            <div v-else-if="el.id === 'price'" class="diy-text diy-price" :style="elTextStyle(el)">{{ priceText(it) }}</div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- 物流打印区 -->
  <Teleport to="body">
    <div id="logistics-print-area" class="print-area">
      <div class="logi-card print-card" :style="logiCardStyle">
        <div
          v-for="el in logiLayout"
          :key="el.id"
          v-show="el.visible"
          class="diy-el"
          :style="elBoxStyle(el)"
        >
          <div v-if="el.id === 'company'" class="diy-text diy-company" :style="elTextStyle(el)">{{ logi.company || '快递公司' }}</div>
          <div v-else-if="el.id === 'track'" class="diy-text diy-track" :style="elTextStyle(el)">{{ logi.track_no }}</div>
          <div v-else-if="el.id === 'recv'" class="diy-text" :style="elTextStyle(el)">
            <div>收件人：{{ logi.recv_name || '' }} {{ logi.recv_phone || '' }}</div>
            <div>{{ logi.recv_addr }}</div>
          </div>
          <div v-else-if="el.id === 'send'" class="diy-text" :style="elTextStyle(el)">
            <div>发件人：{{ currentSender?.sender_name || '' }} {{ currentSender?.phone || '' }}</div>
            <div>{{ currentSender?.address || '' }}</div>
          </div>
          <div v-else-if="el.id === 'remark'" class="diy-text diy-remark" :style="elTextStyle(el)">备注：{{ logi.remark }}</div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import JsBarcode from 'jsbarcode'
import QRCode from 'qrcode'
import { productApi, senderApi, labelTemplateApi } from '../api'

const GOODS_SIZES = [
  { label: '32×19', w: 32, h: 19 }, { label: '35×25', w: 35, h: 25 },
  { label: '40×30', w: 40, h: 30 }, { label: '50×30', w: 50, h: 30 },
  { label: '60×40', w: 60, h: 40 }, { label: '80×50', w: 80, h: 50 },
  { label: '50×70', w: 50, h: 70 }, { label: '90×70', w: 90, h: 70 },
  { label: '100×80', w: 100, h: 80 }, { label: '自定义', w: null, h: null }
]
const LOGI_SIZES = [
  { label: '100×100', w: 100, h: 100 }, { label: '100×150', w: 100, h: 150 },
  { label: '100×180', w: 100, h: 180 }, { label: '76×130', w: 76, h: 130 },
  { label: '76×160', w: 76, h: 160 }, { label: '100×200', w: 100, h: 200 },
  { label: '90×130', w: 90, h: 130 }, { label: '150×230', w: 150, h: 230 },
  { label: '自定义', w: null, h: null }
]

const activeTab = ref('goods')
const spuKeyword = ref('')
const spuOptions = ref([])
const selectedSpuId = ref(null)
const selectedSkuId = ref(null)
const skuOptions = ref([])
const goodsQueue = ref([])

const goodsMode = ref('both')               // 兼容占位（保留字段，布局 DIY 接管显隐）
const goodsSizeIndex = ref(4)               // 默认 60×40（GOODS_SIZES 索引 4，用户确认的默认纸型）
const goodsCustomW = ref(40)
const goodsCustomH = ref(30)
const logiSizeIndex = ref(1)                // 默认 100×150
const logiCustomW = ref(100)
const logiCustomH = ref(150)

const logi = ref({ company: '', track_no: '', recv_name: '', recv_phone: '', recv_addr: '', sender_id: null, remark: '' })
const senders = ref([])

const showSenderModal = ref(false)
const senderForm = ref({ name: '', sender_name: '', phone: '', address: '', remark: '' })

// 打印机偏好（localStorage 持久化）
const goodsPrinter = ref(localStorage.getItem('lbl_goods_printer') || '')
const logiPrinter = ref(localStorage.getItem('lbl_logi_printer') || '')

// 热敏打印机兼容（佳博 GP-2120TUA 等 2 寸热敏机：打印头有效宽约 48mm，60mm 纸两侧各约 6mm 打不出）
const goodsPrintableW = ref(Number(localStorage.getItem('lbl_goods_printable_w')) || 48)
const goodsFitPrintable = ref(localStorage.getItem('lbl_goods_fit_printable') !== '0')
watch([goodsPrintableW, goodsFitPrintable], () => {
  localStorage.setItem('lbl_goods_printable_w', String(goodsPrintableW.value))
  localStorage.setItem('lbl_goods_fit_printable', goodsFitPrintable.value ? '1' : '0')
})
// 可打印宽度安全边距：标签宽 > 打印头可打印宽时，左右各留 (w - pw)/2 白边，内容居中收进中间安全区
const goodsSafePadMm = computed(() => {
  if (!goodsFitPrintable.value) return 0
  const w = goodsSize.value.w
  const pw = Math.max(10, goodsPrintableW.value || 0)
  if (w <= pw) return 0
  return Math.round(((w - pw) / 2) * 10) / 10
})

// 打印确认弹窗
const showPrintModal = ref(false)
const printCtx = ref({ title: '', size: '', printer: '', hint: '', areaId: '', w: 0, h: 0 })

function savePrinterPref() {
  localStorage.setItem('lbl_goods_printer', goodsPrinter.value.trim())
  localStorage.setItem('lbl_logi_printer', logiPrinter.value.trim())
}

const isCustomGoods = computed(() => GOODS_SIZES[goodsSizeIndex.value]?.w == null)
const isCustomLogi = computed(() => LOGI_SIZES[logiSizeIndex.value]?.w == null)

const goodsSize = computed(() => {
  const s = GOODS_SIZES[goodsSizeIndex.value] || GOODS_SIZES[4]
  return isCustomGoods.value
    ? { w: Math.max(10, goodsCustomW.value || 0), h: Math.max(10, goodsCustomH.value || 0) }
    : s
})
const logiSize = computed(() => {
  const s = LOGI_SIZES[logiSizeIndex.value] || LOGI_SIZES[1]
  return isCustomLogi.value
    ? { w: Math.max(30, logiCustomW.value || 0), h: Math.max(30, logiCustomH.value || 0) }
    : s
})

const currentSender = computed(() => senders.value.find(s => s.id === logi.value.sender_id) || null)

// ============================================================
// 布局 DIY 系统（商品/物流各自独立，存 JSON，支持云端模板）
// ============================================================
const FONT_LIST = ['default', 'Microsoft YaHei', 'SimSun', 'SimHei', 'FangSong', 'KaiTi', 'SimLi', 'DengXian']

const DEFAULT_GOODS_LAYOUT = [
  { id: 'barcode', name: '一维码', visible: true, align: 'center', left: 3, top: 5, width: 42, fontSizeMm: 2.2, bold: false, italic: false, underline: false, fontFamily: 'default', scale: 1 },
  { id: 'qrcode', name: '二维码', visible: false, align: 'center', left: 9, top: 26, width: 24, fontSizeMm: 3, bold: false, italic: false, underline: false, fontFamily: 'default', scale: 1 },
  { id: 'name', name: '产品名称', visible: true, align: 'center', left: 3, top: 30, width: 42, fontSizeMm: 3.2, bold: false, italic: false, underline: false, fontFamily: 'Microsoft YaHei', scale: 1 },
  { id: 'price', name: '价格', visible: true, align: 'center', left: 3, top: 25, width: 42, fontSizeMm: 4.2, bold: true, italic: false, underline: false, fontFamily: 'default', scale: 1 }
]

const DEFAULT_LOGI_LAYOUT = [
  { id: 'company', name: '快递公司', visible: true, align: 'left', left: 5, top: 3, width: 90, fontSizeMm: 7, bold: true, italic: false, underline: false, fontFamily: 'Microsoft YaHei', scale: 1 },
  { id: 'track', name: '快递单号', visible: true, align: 'left', left: 5, top: 13, width: 90, fontSizeMm: 4.5, bold: false, italic: false, underline: false, fontFamily: 'Microsoft YaHei', scale: 1 },
  { id: 'recv', name: '收件人区', visible: true, align: 'left', left: 5, top: 28, width: 90, fontSizeMm: 4.6, bold: false, italic: false, underline: false, fontFamily: 'Microsoft YaHei', scale: 1 },
  { id: 'send', name: '发件人区', visible: true, align: 'left', left: 5, top: 88, width: 90, fontSizeMm: 4.6, bold: false, italic: false, underline: false, fontFamily: 'Microsoft YaHei', scale: 1 },
  { id: 'remark', name: '备注', visible: true, align: 'left', left: 5, top: 138, width: 90, fontSizeMm: 4, bold: false, italic: false, underline: false, fontFamily: 'Microsoft YaHei', scale: 1 }
]

function normalizeLayout(arr, type) {
  const defs = type === 'goods' ? DEFAULT_GOODS_LAYOUT : DEFAULT_LOGI_LAYOUT
  if (!Array.isArray(arr) || !arr.length) return defs.map(e => ({ ...e }))
  return defs.map(def => {
    const found = arr.find(a => a && a.id === def.id)
    return { ...def, ...(found || {}) }
  })
}

const goodsLayout = ref(normalizeLayout(null, 'goods'))
const logiLayout = ref(normalizeLayout(null, 'logistics'))
const templates = ref([])
const layoutExpanded = ref(false)   // 布局编辑器内嵌折叠（展开/收起）
const selectedElId = ref(null)

const layoutType = computed(() => activeTab.value === 'goods' ? 'goods' : 'logistics')
const curLayout = computed(() => layoutType.value === 'goods' ? goodsLayout.value : logiLayout.value)
const curSize = computed(() => layoutType.value === 'goods' ? goodsSize.value : logiSize.value)
const goodsCanvasEl = ref(null)
const logiCanvasEl = ref(null)
const selectedEl = computed(() => curLayout.value.find(e => e.id === selectedElId.value) || null)

function fontFamilyCss(f) {
  if (!f || f === 'default') return ''
  return `"${f}"`
}
const FONT_LABELS = {
  'default': '默认',
  'Microsoft YaHei': '微软雅黑',
  'SimSun': '宋体',
  'SimHei': '黑体',
  'FangSong': '仿宋',
  'KaiTi': '楷体',
  'SimLi': '隶书',
  'DengXian': '等线'
}
function fontLabel(f) {
  return FONT_LABELS[f] || f || '默认'
}
function elBoxStyle(el) {
  const sc = el.scale || 1   // 整体缩放（10%~200%）
  return {
    left: `${el.left}mm`, top: `${el.top}mm`,
    width: `${el.width * sc}mm`,
    textAlign: el.align,
    alignItems: el.align === 'left' ? 'flex-start' : el.align === 'right' ? 'flex-end' : 'center'
  }
}
function elTextStyle(el) {
  const s = {}
  const sc = el.scale || 1   // 字号随整体缩放等比变化
  if (el.fontSizeMm) s.fontSize = `${el.fontSizeMm * sc}mm`
  // 文字元素显式水平对齐：不依赖容器 text-align 继承（flex 容器 + width:100% 子元素可能覆盖居中）
  s.textAlign = el.align
  if (el.bold) s.fontWeight = 'bold'
  if (el.italic) s.fontStyle = 'italic'
  if (el.underline) s.textDecoration = 'underline'
  const f = fontFamilyCss(el.fontFamily)
  if (f) s.fontFamily = f
  return s
}
function barcodeImgStyle() { return { width: '100%', height: 'auto' } }
function qrImgStyle() { return { width: '100%', height: 'auto' } }

// ---------- 整体缩放：以元素正中心为锚点（scale 变化时保持几何中心不漂移） ----------
// 估算元素 scale=1 时的框高（mm）：条码=图高16mm+数字行高；二维码=方形图宽(框宽×0.75)；文字=字号×1.15
function estElementHeightMm(el) {
  if (el.id === 'barcode') return 16 + (el.fontSizeMm || 2.2) * 1.15
  if (el.id === 'qrcode') return (el.width || 20) * 0.75
  return (el.fontSizeMm || 3) * 1.15
}
function applyScaleKeepCenter(el, os, ns) {
  if (!el || !os || !ns || os === ns) return
  const h0 = estElementHeightMm(el)
  const w0 = el.width
  const cx = el.left + (w0 * os) / 2   // 缩放前几何中心
  const cy = el.top + (h0 * os) / 2
  el.left = Math.max(0, Math.round((cx - (w0 * ns) / 2) * 10) / 10)
  el.top = Math.max(0, Math.round((cy - (h0 * ns) / 2) * 10) / 10)
}
// 滑块拖动 / 复原按钮 / 任何修改 scale 的地方，统一走中心锚点（保持元素正中心不动）
watch(() => selectedEl.value?.scale, (ns, os) => {
  const el = selectedEl.value
  if (!el || el.scale == null) return
  if (!os || os === 0) return   // 首次绑定/模板加载不视为缩放操作
  applyScaleKeepCenter(el, os, ns)
})

// ---------- 布局编辑器：拖拽 / 缩放 ----------
const pxPerMm = ref(3.78)
const dragRef = ref(null)   // { el, kind:'move'|'resize', startX, startY, left, top, width }

function canvasRect() {
  const el = layoutType.value === 'goods' ? goodsCanvasEl.value : logiCanvasEl.value
  return el ? el.getBoundingClientRect() : null
}
function startDrag(e, el) {
  e.preventDefault()
  selectedElId.value = el.id
  const r = canvasRect()
  pxPerMm.value = r ? r.width / curSize.value.w : 3.78
  dragRef.value = { el, kind: 'move', startX: e.clientX, startY: e.clientY, left: el.left, top: el.top, width: el.width }
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}
function startResize(e, el) {
  e.preventDefault(); e.stopPropagation()
  selectedElId.value = el.id
  const r = canvasRect()
  pxPerMm.value = r ? r.width / curSize.value.w : 3.78
  dragRef.value = { el, kind: 'resize', startX: e.clientX, startY: e.clientY, left: el.left, top: el.top, width: el.width }
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}
function onDragMove(e) {
  const d = dragRef.value
  if (!d) return
  const dxMm = (e.clientX - d.startX) / pxPerMm.value
  const dyMm = (e.clientY - d.startY) / pxPerMm.value
  if (d.kind === 'move') {
    d.el.left = Math.max(0, Math.round((d.left + dxMm) * 10) / 10)
    d.el.top = Math.max(0, Math.round((d.top + dyMm) * 10) / 10)
  } else {
    d.el.width = Math.max(4, Math.round((d.width + dxMm) * 10) / 10)
  }
}
function onDragEnd() {
  dragRef.value = null
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
}
onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
})

// ---------- 模板管理（后端云端，跟随账号） ----------
async function loadTemplates() {
  templates.value = await labelTemplateApi.list({ type: layoutType.value })
}
function applyLayoutArr(arr) {
  const target = layoutType.value === 'goods' ? goodsLayout : logiLayout
  target.value = normalizeLayout(arr, layoutType.value)
}
async function applyDefaultTemplate() {
  try {
    const tpl = await labelTemplateApi.getDefault({ type: layoutType.value })
    if (tpl) {
      applyLayoutArr(JSON.parse(tpl.data))
    } else {
      applyLayoutArr(null)
    }
  } catch (e) {
    applyLayoutArr(null)
  }
}
async function saveAsDefaultTemplate() {
  const data = JSON.stringify(curLayout.value)
  const existing = templates.value.find(t => t.is_default)
  try {
    if (existing) {
      await labelTemplateApi.update(existing.id, { data, is_default: true })
    } else {
      await labelTemplateApi.create({
        name: layoutType.value === 'goods' ? '商品标签默认' : '物流面单默认',
        type: layoutType.value, data, is_default: true
      })
    }
    await loadTemplates()
    await applyDefaultTemplate()
    alert('已保存为默认模板并自动套用')
  } catch (e) {
    alert(e.response?.data?.detail || '保存模板失败')
  }
}
async function saveAsNamedTemplate() {
  const name = prompt('请输入模板名：')
  if (!name) return
  try {
    await labelTemplateApi.create({
      name, type: layoutType.value, data: JSON.stringify(curLayout.value), is_default: false
    })
    await loadTemplates()
    alert('模板已保存')
  } catch (e) {
    alert(e.response?.data?.detail || '保存模板失败')
  }
}
async function applyTemplate(tpl) {
  try {
    applyLayoutArr(JSON.parse(tpl.data))
  } catch (e) {
    alert('模板数据损坏，无法套用')
  }
}
async function renameTemplate(tpl) {
  const name = prompt('新模板名：', tpl.name)
  if (!name) return
  try {
    await labelTemplateApi.update(tpl.id, { name })
    await loadTemplates()
  } catch (e) {
    alert(e.response?.data?.detail || '重命名失败')
  }
}
async function removeTemplate(tpl) {
  if (!confirm(`确定删除模板「${tpl.name}」？`)) return
  try {
    await labelTemplateApi.remove(tpl.id)
    await loadTemplates()
  } catch (e) {
    alert(e.response?.data?.detail || '删除失败')
  }
}
function toggleLayoutEditor() {
  layoutExpanded.value = !layoutExpanded.value
  if (layoutExpanded.value) {
    loadTemplates()
  } else {
    selectedElId.value = null
  }
}

// ---------- 商品打印内容模式（仅一维码 / 仅二维码 / 一维码+二维码） ----------
const goodsModeState = computed(() => {
  const b = goodsLayout.value.find(e => e.id === 'barcode')
  const q = goodsLayout.value.find(e => e.id === 'qrcode')
  const bVis = !!b?.visible
  const qVis = !!q?.visible
  if (bVis && qVis) return 'both'
  if (bVis) return 'barcode'
  if (qVis) return 'qrcode'
  return 'both'  // 都关时默认高亮「一维码 + 二维码」
})

function setGoodsMode(mode) {
  const b = goodsLayout.value.find(e => e.id === 'barcode')
  const q = goodsLayout.value.find(e => e.id === 'qrcode')
  if (!b || !q) return
  if (mode === 'barcode') { b.visible = true; q.visible = false }
  else if (mode === 'qrcode') { b.visible = false; q.visible = true }
  else { b.visible = true; q.visible = true }
}

// ---------- 自动排版：三段式（上条码 / 中价格 / 下名称），整组垂直居中，宽度适配可打印区 ----------
function autoLayoutGoods() {
  const { w, h } = goodsSize.value
  const pad = goodsSafePadMm.value
  // 元素应落在 print-safe 中间可打印区内（左右留白 pad）
  const printableW = Math.max(10, w - pad * 2)
  const elW = Math.max(10, Math.round(printableW * 0.9 * 10) / 10)
  const left = Math.round(((printableW - elW) / 2) * 10) / 10
  const find = id => goodsLayout.value.find(e => e.id === id)
  const barcode = find('barcode')
  const price = find('price')
  const name = find('name')
  if (!barcode || !price || !name) return
  const qrcode = find('qrcode')
  if (qrcode) qrcode.visible = false   // 三段式已占满，自动排版时收起二维码（可在模式按钮中重新开启）
  // 各块估算高度（mm）：条码图+数字约 19mm；价格/名称按字号×1.5 行高
  const barH = 19
  const priceH = Math.round(price.fontSizeMm * 1.5 * 10) / 10
  const nameH = Math.round(name.fontSizeMm * 1.5 * 10) / 10
  const totalH = barH + priceH + nameH
  const startTop = Math.max(0, Math.round(((h - totalH) / 2) * 10) / 10)
  ;[barcode, price, name].forEach(el => {
    el.left = left
    el.width = elW
    el.align = 'center'
    el.visible = true
  })
  barcode.top = startTop
  price.top = Math.round((startTop + barH) * 10) / 10
  name.top = Math.round((startTop + barH + priceH) * 10) / 10
  if (qrcode) {
    qrcode.left = left
    qrcode.top = Math.round((startTop + barH) * 10) / 10
    qrcode.width = Math.round(elW * 0.5 * 10) / 10
    qrcode.align = 'center'
  }
}

// ---------- 商品搜索 ----------
async function searchSpus() {
  const params = { keyword: spuKeyword.value.trim() }
  spuOptions.value = await productApi.list(params)
  selectedSpuId.value = null
  skuOptions.value = []
  selectedSkuId.value = null
}

function onSpuChange() {
  const spu = spuOptions.value.find(s => s.id === selectedSpuId.value)
  skuOptions.value = spu?.skus || []
  selectedSkuId.value = skuOptions.value[0]?.id ?? null
}

function addToQueue() {
  const spu = spuOptions.value.find(s => s.id === selectedSpuId.value)
  const sku = skuOptions.value.find(k => k.id === selectedSkuId.value)
  if (!spu || !sku) return
  goodsQueue.value.push({ spu, sku, barcodeUrl: '', qrUrl: '' })
}

// ---------- 商品标签图片生成 ----------
function priceText(it) {
  return `¥${Number(it.sku.sale_price || 0).toFixed(2)}`
}

function qrText(spu, sku) {
  const s = spu
  const k = sku
  const lines = [`名称：${s.name}`]
  if (s.designer) lines.push(`设计者：${s.designer}`)
  if (s.production_date) lines.push(`生产日期：${s.production_date}`)
  if (s.material) lines.push(`材质：${s.material}`)
  lines.push(`重量：${s.weight || 0}${s.weight_unit || ''}`)
  if (s.code) lines.push(`型号：${s.code}`)
  if (k.spec_name) lines.push(`规格：${k.spec_name}`)
  if (s.remark) lines.push(`备注：${s.remark}`)
  return lines.join('\n')
}

// 生成单个商品的条码/二维码图片（队列 & 画布示例共用）
async function buildItemContent(spu, sku) {
  const item = { barcodeUrl: '', qrUrl: '' }
  if (!spu || !sku) return item
  const canvas = document.createElement('canvas')
  try {
    JsBarcode(canvas, sku.sku_code || sku.barcode || '0000000000000', {
      format: 'CODE128', width: 2, height: 60, displayValue: true,
      fontSize: 16, margin: 4, background: '#ffffff'
    })
    item.barcodeUrl = canvas.toDataURL('image/png')
  } catch (e) {
    item.barcodeUrl = ''
  }
  try {
    item.qrUrl = await QRCode.toDataURL(qrText(spu, sku), { width: 360, margin: 1, errorCorrectionLevel: 'M', color: { dark: '#000000', light: '#ffffff' } })
  } catch (e) {
    item.qrUrl = ''
  }
  return item
}

async function renderQueue() {
  for (const it of goodsQueue.value) {
    const c = await buildItemContent(it.spu, it.sku)
    it.barcodeUrl = c.barcodeUrl
    it.qrUrl = c.qrUrl
  }
}

// 布局画布示例商品：优先取队列第一项；队列为空时用当前选中的商品实时渲染
const canvasDemo = ref(null)
async function refreshCanvasDemo() {
  let src = null
  if (goodsQueue.value.length) {
    src = goodsQueue.value[0]
  } else if (selectedSpuId.value && selectedSkuId.value) {
    const spu = spuOptions.value.find(s => s.id === selectedSpuId.value)
    const sku = skuOptions.value.find(k => k.id === selectedSkuId.value)
    if (spu && sku) {
      const c = await buildItemContent(spu, sku)
      src = { spu, sku, barcodeUrl: c.barcodeUrl, qrUrl: c.qrUrl }
    }
  }
  canvasDemo.value = src
}
watch([goodsQueue, selectedSpuId, selectedSkuId], refreshCanvasDemo, { deep: true })

// ---------- 尺寸切换自动缩放布局（大→小/小→大 元素始终落在画布内，可逆不漂移） ----------
function scaleLayoutToFit(layoutArr, from, to) {
  if (!from || !to || !from.w || !from.h || !to.w || !to.h) return
  const sx = to.w / from.w   // 宽方向比例
  const sy = to.h / from.h   // 高方向比例
  const sf = Math.min(sx, sy) // 字号取较小比例，避免文字溢出
  for (const el of layoutArr) {
    el.left = Math.round(el.left * sx * 10) / 10
    el.top = Math.round(el.top * sy * 10) / 10
    el.width = Math.max(4, Math.round(el.width * sx * 10) / 10)
    el.fontSizeMm = Math.max(0.5, Math.round(el.fontSizeMm * sf * 10) / 10)
  }
}
// 商品 / 物流 尺寸（含自定义尺寸）变化时，自动按比例缩放对应布局元素
watch(goodsSize, (ns, os) => {
  if (os && (os.w !== ns.w || os.h !== ns.h)) {
    scaleLayoutToFit(goodsLayout.value, os, ns)
  }
})
watch(logiSize, (ns, os) => {
  if (os && (os.w !== ns.w || os.h !== ns.h)) {
    scaleLayoutToFit(logiLayout.value, os, ns)
  }
})

// ---------- 尺寸自适应样式 ----------
const goodsCardStyle = computed(() => {
  const { w, h } = goodsSize.value
  return { width: `${w}mm`, height: `${h}mm` }
})

// 热敏打印头兼容：内容整体收进中间可打印区（绝对定位元素不受父 padding 影响，需用 wrapper 平移）
const printSafeStyle = computed(() => {
  const pad = goodsSafePadMm.value
  return { left: `${pad}mm`, right: `${pad}mm`, top: 0, bottom: 0 }
})

const logiCardStyle = computed(() => {
  const { w, h } = logiSize.value
  return { width: `${w}mm`, height: `${h}mm` }
})

// ---------- 打印 ----------
function applyPageSize(w, h) {
  let el = document.getElementById('label-page-style')
  if (!el) {
    el = document.createElement('style')
    el.id = 'label-page-style'
    document.head.appendChild(el)
  }
  el.textContent = `@page { size: ${w}mm ${h}mm; margin: 0; }`
}

function openPrintModal(type) {
  if (type === 'goods') {
    if (!goodsQueue.value.length) return
    printCtx.value = {
      title: '商品标签打印',
      size: `${goodsSize.value.w}×${goodsSize.value.h}mm`,
      printer: goodsPrinter.value.trim(),
      hint: '热敏小票机（如乐名）',
      areaId: 'goods-print-area',
      w: goodsSize.value.w, h: goodsSize.value.h,
      compatPad: goodsSafePadMm.value,
      printableW: goodsPrintableW.value
    }
  } else {
    printCtx.value = {
      title: '物流面单打印',
      size: `${logiSize.value.w}×${logiSize.value.h}mm`,
      printer: logiPrinter.value.trim(),
      hint: '快递面单大打印机',
      areaId: 'logistics-print-area',
      w: logiSize.value.w, h: logiSize.value.h,
      compatPad: 0,
      printableW: 0
    }
  }
  showPrintModal.value = true
}

function doPrint() {
  const ctx = printCtx.value
  showPrintModal.value = false
  applyPageSize(ctx.w, ctx.h)
  document.getElementById('goods-print-area')?.classList.remove('print-on')
  document.getElementById('logistics-print-area')?.classList.remove('print-on')
  document.getElementById(ctx.areaId)?.classList.add('print-on')
  // 等一帧让 class 生效
  setTimeout(() => {
    window.print()
    document.getElementById(ctx.areaId)?.classList.remove('print-on')
  }, 60)
}

// ---------- 发件人 ----------
async function loadSenders() {
  senders.value = await senderApi.list()
}

async function saveSender() {
  if (!senderForm.value.sender_name.trim()) { alert('请填写发件人姓名'); return }
  try {
    const created = await senderApi.create({ ...senderForm.value })
    await loadSenders()
    logi.value.sender_id = created.id
    showSenderModal.value = false
    senderForm.value = { name: '', sender_name: '', phone: '', address: '', remark: '' }
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

function switchTab(t) {
  activeTab.value = t
}

watch([goodsQueue], async () => {
  if (activeTab.value === 'goods' && goodsQueue.value.length) {
    await nextTick()
    await renderQueue()
  }
}, { deep: true })

onMounted(async () => {
  await Promise.all([searchSpus(), loadSenders()])
  await applyDefaultTemplate()
})
</script>

<style scoped>
.lbl-tabs { display: flex; gap: 8px; margin: 14px 0; }
.lbl-tabs button {
  height: 36px; padding: 0 22px; border-radius: 9px; cursor: pointer;
  border: 1px solid var(--border); background: rgba(255,255,255,.04); color: var(--text-2);
  font-size: 14px;
}
.lbl-tabs button.active {
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  color: #fff; border-color: transparent;
}
.lbl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 18px; }
.fitem { display: flex; flex-direction: column; gap: 6px; }
.fitem label { font-size: 13px; color: var(--text-2); }
.fitem input, .fitem select {
  height: 38px; padding: 0 12px; border-radius: 9px;
  border: 1px solid var(--border); background: rgba(255,255,255,.06);
  color: var(--text); font-size: 14px; outline: none;
}
.fitem input:focus, .fitem select:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(91,124,250,.18); }
.fitem select option { background: #161b38; color: var(--text); }
.unit-row { display: flex; gap: 8px; align-items: center; }
.unit-row select { flex: 1; }
.unit-row input { flex: 1; }
.radio-row { display: flex; gap: 16px; flex-wrap: wrap; }
.radio-row label { font-size: 14px; color: var(--text); display: flex; align-items: center; gap: 5px; cursor: pointer; }
.radio-row input { accent-color: var(--primary); }
/* ============ 热敏打印机兼容设置 ============ */
.compat-box {
  padding: 12px 14px; border-radius: 10px;
  border: 1px dashed rgba(255, 140, 80, 0.45);
  background: rgba(255, 140, 80, 0.06);
}
.compat-box > label {
  display: flex; align-items: center; font-size: 13px; color: var(--text);
  cursor: pointer;
}
/* 内容 wrapper：绝对定位基准，把商品元素整体收进中间可打印区 */
.print-safe { position: absolute; overflow: hidden; z-index: 2; }
/* 打印确认弹窗内的兼容操作提示 */
.pc-compat {
  margin-top: 14px; text-align: left; padding: 12px 14px; border-radius: 10px;
  background: rgba(255, 140, 80, 0.08); border: 1px solid rgba(255, 140, 80, 0.45);
  line-height: 1.8;
}
.pc-compat-title { font-size: 13px; font-weight: 700; color: #d9702f; margin-bottom: 6px; }
.pc-compat-steps { font-size: 12.5px; color: var(--text-2); }
.pc-compat-steps div::before { content: "· "; color: #d9702f; }
/* ============ 打印内容模式按钮 ============ */
.mode-btn-row { display: flex; gap: 8px; flex-wrap: wrap; }
.mode-btn {
  flex: 1; min-width: 96px; height: 38px; border-radius: 9px; cursor: pointer;
  border: 1px solid var(--border); background: rgba(255,255,255,.04);
  color: var(--text-2); font-size: 13px;
}
.mode-btn.active {
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  color: #fff; border-color: transparent;
}
/* ============ 布局设置内嵌折叠面板 ============ */
.layout-toggle {
  display: flex; align-items: center; justify-content: space-between;
  height: 42px; padding: 0 14px; border-radius: 9px; cursor: pointer;
  border: 1px solid var(--border); background: rgba(255,255,255,.04);
  user-select: none;
}
.layout-toggle-title { font-size: 14px; color: var(--text); }
.layout-toggle-arrow { font-size: 12px; color: var(--primary); }
.layout-embed {
  margin-top: 10px; padding: 16px; border-radius: 12px;
  border: 1px solid var(--border); background: rgba(255,255,255,.03);
}
.layout-embed .layout-main { margin-top: 0; }
.mini-btn {
  height: 34px; padding: 0 12px; border-radius: 8px;
  border: 1px solid rgba(91,124,250,.5); background: transparent;
  color: var(--primary); font-size: 13px; cursor: pointer;
}
.mini-btn.danger { border-color: rgba(255,92,92,.5); color: #ff7b7b; }
.queue-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.queue-list .tag {
  display: inline-flex; align-items: center; padding: 4px 12px;
  border-radius: 999px; background: rgba(91,124,250,.14);
  border: 1px solid rgba(91,124,250,.4); font-size: 13px; color: var(--text);
}
.sender-preview {
  margin-top: 6px; font-size: 12px; color: var(--text-2); line-height: 1.7;
  padding: 8px 10px; border-radius: 8px; background: rgba(255,255,255,.04);
  border: 1px dashed var(--border);
}
.btn-print {
  height: 42px; padding: 0 28px; border: none; border-radius: 10px;
  color: #fff; font-size: 15px; font-weight: 600; cursor: pointer;
  background: linear-gradient(135deg, var(--gold), #d99a3f);
  box-shadow: 0 8px 22px rgba(226,180,92,.28);
}
.preview-wrap { margin-top: 10px; }
.preview-sheet {
  display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-start;
  padding: 14px; border-radius: 12px;
  background: repeating-linear-gradient(45deg, #10132b, #10132b 10px, #141834 10px, #141834 20px);
}
/* ============ 商品标签卡（mm 单位，所见即所得） ============ */
.goods-card {
  background: #ffffff; color: #000;
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 0.6mm;
  padding: 1mm; box-sizing: border-box;
  overflow: hidden; border-radius: 1mm;
  box-shadow: 0 4px 14px rgba(0,0,0,.35);
  position: relative;
}
.goods-card .bc-box { display: flex; justify-content: center; width: 100%; }
.goods-card .bc-box img { max-width: 92%; height: auto; max-height: 46%; }
.goods-card .qr-box { display: flex; justify-content: center; width: 100%; }
.goods-card .qr-img { width: 62%; height: auto; object-fit: contain; }
.goods-card .g-price { font-weight: 700; color: #c00; font-size: var(--g-price-size); line-height: 1.1; }
.goods-card .g-name {
  font-size: var(--g-name-size); line-height: 1.15; text-align: center;
  width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
/* ============ 物流标签卡（快递面单布局） ============ */
.logi-card {
  background: #ffffff; color: #000;
  display: flex; flex-direction: column; box-sizing: border-box;
  padding: 4mm 5mm; overflow: hidden; border-radius: 1mm;
  box-shadow: 0 4px 14px rgba(0,0,0,.35);
  position: relative;
}
.logi-head {
  display: flex; justify-content: space-between; align-items: baseline;
  border-bottom: 0.6mm solid #000; padding-bottom: 2mm;
}
.logi-company { font-size: 7mm; font-weight: 800; letter-spacing: 1mm; }
.logi-track { font-size: 4mm; font-weight: 600; letter-spacing: 0.5mm; }
.logi-body { flex: 1; display: flex; flex-direction: column; gap: 5mm; padding-top: 4mm; }
.logi-recv, .logi-send { display: flex; flex-direction: column; gap: 1.4mm; }
.logi-caption { font-size: 4mm; color: #666; letter-spacing: 0.8mm; }
.logi-name { font-size: 7mm; font-weight: 800; }
.logi-phone { font-size: 5mm; font-weight: 600; }
.logi-addr { font-size: 4.6mm; line-height: 1.4; color: #222; }
.logi-remark {
  font-size: 4mm; border-top: 0.4mm dashed #999; padding-top: 2mm; color: #333;
}
/* ============ 布局 DIY 元素（绝对定位，相对卡片定位） ============ */
.diy-el {
  position: absolute; box-sizing: border-box;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.diy-text { width: 100%; line-height: 1.15; overflow: hidden; }
.diy-price { color: #c00; font-weight: 700; }
/* 条码/二维码图片最大宽度收窄，为水平对齐（left/center/right）留出视觉空间；容器 .diy-el/.layout-el 的 align-items 由 elBoxStyle 按 align 映射驱动，三处（画布/预览/打印）一致 */
.diy-barcode-img { max-width: 92%; height: auto; }
/* 条码数字显式 text-align（elTextStyle 已注入 el.align），不再硬编码居中 */
.diy-barcode-text { width: 100%; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
/* 二维码图片最大 75% 宽，配合容器 align-items 映射实现左/中/右对齐 */
.diy-qrcode-img { max-width: 75%; height: auto; }
.diy-company { font-weight: 800; letter-spacing: 1mm; }
.diy-track { font-weight: 600; letter-spacing: 0.5mm; }
.diy-remark { border-top: 0.4mm dashed #999; padding-top: 2mm; }
/* ============ 打印控制（print-on 由 JS 动态加） ============ */
.print-area { display: none; }
/* 注意：@media print 中的全局选择器（body、html/body）必须在非 scoped style 块中定义，
   否则 scoped 会加组件属性导致无法命中组件外的布局元素 */
/* ============ 弹窗 ============ */
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(5, 7, 18, 0.72); backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center; z-index: 50;
}
.modal {
  width: 460px; max-width: 92vw; max-height: 80vh; overflow: auto;
  background: var(--panel-strong); border: 1px solid var(--border);
  border-radius: 14px; padding: 22px 24px; box-shadow: 0 24px 70px rgba(0,0,0,.6);
}
.modal h3 { margin-bottom: 14px; letter-spacing: 1px; }
.modal-form { display: flex; flex-direction: column; gap: 12px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.modal-actions button {
  height: 38px; padding: 0 22px; border: none; border-radius: 9px;
  color: #fff; font-size: 14px; cursor: pointer;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
}
.modal-actions .btn-plain { background: transparent; border: 1px solid var(--border); color: var(--text-2); }

/* ============ 打印机偏好区 ============ */
.printer-pref { margin-bottom: 14px; }
.pref-title {
  font-size: 13px; color: var(--gold); letter-spacing: 0.5px;
  margin-bottom: 12px; display: flex; align-items: center; gap: 8px;
}
.pref-title::before {
  content: ""; width: 4px; height: 14px; border-radius: 2px;
  background: linear-gradient(180deg, var(--gold), #d99a3f);
}
.pref-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 18px; }

/* ============ 打印确认弹窗 ============ */
.print-confirm { text-align: center; }
.print-confirm h3 { letter-spacing: 2px; }
.pc-type {
  font-size: 24px; font-weight: 800; letter-spacing: 2px; margin-top: 16px;
  background: linear-gradient(120deg, #fff, var(--gold));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.pc-size { margin-top: 8px; font-size: 15px; color: var(--text); }
.pc-printer {
  margin-top: 14px; padding: 12px 16px; border-radius: 10px;
  background: rgba(226, 180, 92, 0.10); border: 1px solid rgba(226, 180, 92, 0.4);
  font-size: 15px; color: var(--text-2); line-height: 1.6;
}
.pc-printer .pc-name { color: var(--gold); font-size: 18px; letter-spacing: 0.5px; }
.print-confirm .muted { margin-top: 12px; }
.pc-go {
  background: linear-gradient(135deg, var(--gold), #d99a3f) !important;
  box-shadow: 0 6px 18px rgba(226, 180, 92, 0.3);
}

/* ============ 布局编辑器 ============ */
.layout-modal { width: 900px; max-width: 96vw; }
.layout-main { display: flex; gap: 18px; margin-top: 14px; }
.layout-canvas-wrap { flex: 1; min-width: 0; }
.layout-canvas {
  position: relative; background: #fff; border: 1px solid var(--border);
  border-radius: 6px; margin: 0 auto; overflow: hidden;
}
.layout-el {
  position: absolute; box-sizing: border-box;
  border: 1px dashed rgba(91, 124, 250, 0.55);
  display: flex; align-items: center; justify-content: center;
  cursor: move; color: #000; font-size: 12px;
  background: rgba(91, 124, 250, 0.06);
}
/* 真实渲染模式：画布直接显示实际打印内容（条码图/文字），虚线框仅 hover/选中时出现 */
.layout-el.real {
  border-color: transparent; background: transparent;
  flex-direction: column; color: #000;
}
.layout-el.real:hover { border-color: rgba(91, 124, 250, 0.55); background: rgba(91,124,250,.05); }
.layout-el.active { border: 1px solid var(--gold); background: rgba(226, 180, 92, 0.12); }
/* 隐藏元素彻底消失（不占位、不遮挡拖拽），通过右侧「元素列表」或模式按钮恢复 */
.layout-el.hidden { display: none !important; }
.layout-el-label {
  display: inline-block; max-width: 80%; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; padding: 2px 4px;
  background: rgba(255,255,255,.7); border-radius: 4px; color: #333;
}
/* 元素名字浮标：hover / 选中时显示在元素上方，便于识别正在编辑哪个元素 */
.layout-el-name {
  position: absolute; left: 0; top: 0; transform: translateY(-100%);
  display: none; font-size: 10px; line-height: 1.4; color: #fff;
  background: rgba(91, 124, 250, 0.9); padding: 1px 6px;
  border-radius: 4px; white-space: nowrap; z-index: 5;
  pointer-events: none;
}
.layout-el.real:hover .layout-el-name, .layout-el.active .layout-el-name { display: block; }
.layout-el-resize {
  position: absolute; right: 0; bottom: 0; width: 10px; height: 10px;
  background: var(--gold); border-radius: 2px; cursor: nwse-resize;
}
.layout-canvas-tip {
  position: absolute; left: 0; right: 0; top: 50%; transform: translateY(-50%);
  text-align: center; font-size: 13px; color: #666;
}
/* 热敏打印头兼容安全区：灰底区为打印头打不到的左右边距，元素应居中放在中间可打印区 */
.printable-guide {
  position: absolute; top: 0; bottom: 0; z-index: 1;
  border-left: 1px dashed rgba(255, 140, 80, 0.85);
  border-right: 1px dashed rgba(255, 140, 80, 0.85);
  pointer-events: none;
  background: linear-gradient(90deg,
    rgba(0,0,0,0.10) 0, rgba(0,0,0,0.10) 100%);
  background-size: 100% 100%;
}
.printable-guide-tag {
  position: absolute; top: 0; left: 50%; transform: translateX(-50%);
  font-size: 10px; line-height: 1.5; color: #b4552a; background: #fff7f0;
  border: 1px solid rgba(255, 140, 80, 0.6); border-radius: 0 0 4px 4px;
  padding: 0 6px; white-space: nowrap;
}
.layout-panel { width: 300px; flex-shrink: 0; max-height: 60vh; overflow: auto; }
/* 元素列表（含隐藏元素，便于恢复） */
.lp-el-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.lp-el-chip {
  padding: 4px 10px; border-radius: 999px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--border); color: var(--text-2); background: rgba(255,255,255,.04);
  user-select: none;
}
.lp-el-chip.on { border-color: var(--gold); color: var(--gold); background: rgba(226,180,92,.1); }
.lp-el-chip.off { opacity: .55; }
.lp-el-chip:hover { border-color: var(--primary); color: var(--primary); }
.lp-title { font-size: 13px; color: var(--text); font-weight: 600; margin-bottom: 8px; letter-spacing: 0.5px; }
.lp-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.lp-row label { width: 88px; flex-shrink: 0; font-size: 12px; color: var(--text-2); }
.lp-row input[type="number"], .lp-row select {
  flex: 1; height: 32px; padding: 0 8px; border-radius: 7px;
  border: 1px solid var(--border); background: rgba(255,255,255,.06);
  color: var(--text); font-size: 13px; outline: none;
}
.lp-row input[type="checkbox"] { accent-color: var(--primary); }
.lp-check-group { gap: 14px; }
.lp-scale-val { font-size: 12px; color: var(--primary); font-weight: 600; min-width: 34px; text-align: right; }
.lp-check-group label { width: auto; display: flex; align-items: center; gap: 4px; cursor: pointer; }
.lp-divider { height: 1px; background: var(--border); margin: 14px 0; }
.lp-tpl-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.lp-tpl-item { display: flex; align-items: center; gap: 6px; }
.lp-tpl-name {
  flex: 1; font-size: 13px; color: var(--text); cursor: pointer; padding: 4px 6px;
  border-radius: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.lp-tpl-name:hover { background: rgba(91, 124, 250, 0.12); }
.lp-tpl-name.is-default { color: var(--gold); }
.lp-actions { display: flex; gap: 8px; }
.lp-save-default { flex: 1; }
</style>

<!-- ============ 打印全局样式（非 scoped，必须命中 body/侧边栏等组件外元素） ============ -->
<style>
@media print {
  /* 多页 bug 修复：将整个后台布局容器彻底移出文档流，隐藏元素不再占位撑页。
     否则仅 visibility:hidden 的页面仍占满数页导致打印多张空白纸 */
  body > #app { display: none !important; }
  body > .layout, .layout, .sidebar, .main { display: none !important; }
  html, body { background: #fff !important; }
  /* 打印区 Teleport 到 body 直接子级：改为正常文档流，不再 fixed 锚定左上角。
     fixed 元素脱离文档流，打印分页计算以视口/页面为基准，与卡片高度（=页面高度）冲突，
     会把 60×40 单张标签溢出排到第二张纸。回到文档流后卡片尺寸与 @page 尺寸一致，一张自然占一页。 */
  .print-area.print-on {
    display: block !important;
    position: static !important;
    left: auto; top: auto; margin: 0 !important;
  }
  /* 打印卡片去除阴影与圆角，白底黑字。
     强制分页仅作用于打印区内的多张场景：前 N-1 张 break-after:page，最后一张自动，
     保证单张恰好一页、多张每张一页依次排列，不产生多余空白页 */
  .print-area.print-on .print-card {
    box-shadow: none !important;
    border-radius: 0 !important;
    page-break-after: always;
    break-after: page;
  }
  .print-area.print-on .print-card:last-child { page-break-after: auto; break-after: auto; }
}
</style>

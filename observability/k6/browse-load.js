/**
 * 浏览链路混合负载（只读为主）。
 *
 * 用户模型参考电商真实流量：
 *   40% 商品列表翻页（首页/分类页瀑布流）
 *   25% 关键词搜索（含少量无结果冷门词，模拟热点倾斜）
 *   20% 商品详情
 *   15% 首页聚合（品牌 + 运营位 + 推荐流，接口最重的只读路径）
 * 登录可用时叠加：类目、我的、购物车、订单、收藏、浏览历史读取。
 *
 * 用法：
 *   k6 run -e BASE_URL=http://111.170.33.2:60084/api \
 *          -e PHONE=13800000001 \
 *          -e STAGES=30s:10,2m:50,3m:100 k6/browse-load.js
 */
import http from 'k6/http';
import { sleep } from 'k6';
import { Trend } from 'k6/metrics';
import {
  buildOptions,
  customerLogin,
  expectOk,
  getBaseUrl,
  getPhone,
  jsonHeaders,
  loadSpuIds,
  pickRandom,
  randomInt,
  thinkTime,
  verifyTokenUsable,
} from './lib/shang.js';

const endpointTrends = {
  home: new Trend('endpoint_home_duration'),
  products: new Trend('endpoint_products_duration'),
  search: new Trend('endpoint_search_duration'),
  detail: new Trend('endpoint_detail_duration'),
  categories: new Trend('endpoint_categories_duration'),
  me: new Trend('endpoint_me_duration'),
  cart: new Trend('endpoint_cart_duration'),
  orders: new Trend('endpoint_orders_duration'),
  favorites: new Trend('endpoint_favorites_duration'),
};

export const options = buildOptions(20, '3m');

// 关键词取自种子商品的真实名称（搜索按名称匹配）；
// 最后一个是不存在的词，用来观察"无结果"分支的响应时间。
const KEYWORDS = ['帐篷', '咖啡', '笔记本', '口红', '跑步鞋', 'zzz不存在'];

export function setup() {
  const baseUrl = getBaseUrl();
  const spuIds = loadSpuIds(baseUrl, '', 40);

  let token = '';
  let authNote = '未启用鉴权链路';

  const login = customerLogin(baseUrl, getPhone(), __ENV.CODE || '123456');
  if (login.token) {
    const verdict = verifyTokenUsable(baseUrl, login.token, '/me');
    if (verdict.usable) {
      token = login.token;
      authNote = '鉴权可用，已叠加受保护读链路';
    } else {
      authNote = `鉴权不可用（${verdict.detail}），降级为公开读链路`;
    }
  } else if (login.reason) {
    authNote = `登录未成功（${login.reason}），降级为公开读链路`;
  }

  console.log(`[browse-load] 商品池 ${spuIds.length} 条；${authNote}`);

  return { baseUrl, token, spuIds };
}

export default function (data) {
  const baseUrl = data.baseUrl;
  const token = data.token;
  const roll = Math.random();

  if (roll < 0.4) {
    const page = randomInt(1, 4);
    const size = randomInt(8, 20);
    const response = http.get(`${baseUrl}/products?page=${page}&size=${size}`, jsonHeaders(token));
    endpointTrends.products.add(response.timings.duration);
    expectOk(response, 'products list');
  } else if (roll < 0.65) {
    const keyword = pickRandom(KEYWORDS);
    const response = http.get(
      `${baseUrl}/search?q=${encodeURIComponent(keyword)}&page=1&size=10`,
      jsonHeaders(token),
    );
    endpointTrends.search.add(response.timings.duration);
    expectOk(response, 'search');
  } else if (roll < 0.85) {
    const spuId = pickRandom(data.spuIds);
    if (spuId !== null) {
      const response = http.get(`${baseUrl}/products/${spuId}`, jsonHeaders(token));
      endpointTrends.detail.add(response.timings.duration);
      expectOk(response, 'product detail');
    }
  } else {
    // 首页聚合：品牌 + 运营位 + 推荐流，一次请求里包含多段查询
    const response = http.get(`${baseUrl}/home`, jsonHeaders(token));
    endpointTrends.home.add(response.timings.duration);
    expectOk(response, 'home');
  }

  if (token) {
    const extra = Math.random();
    if (extra < 0.3) {
      const response = http.get(`${baseUrl}/categories`, jsonHeaders(token));
      endpointTrends.categories.add(response.timings.duration);
      expectOk(response, 'categories');
    } else if (extra < 0.5) {
      const response = http.get(`${baseUrl}/me`, jsonHeaders(token));
      endpointTrends.me.add(response.timings.duration);
      expectOk(response, 'current customer');
    } else if (extra < 0.7) {
      const response = http.get(`${baseUrl}/cart`, jsonHeaders(token));
      endpointTrends.cart.add(response.timings.duration);
      expectOk(response, 'cart');
    } else if (extra < 0.85) {
      const response = http.get(`${baseUrl}/orders?page=1&size=5`, jsonHeaders(token));
      endpointTrends.orders.add(response.timings.duration);
      expectOk(response, 'orders');
    } else {
      const response = http.get(`${baseUrl}/favorites?page=1&size=10`, jsonHeaders(token));
      endpointTrends.favorites.add(response.timings.duration);
      expectOk(response, 'favorites');
    }
  }

  sleep(thinkTime());
}

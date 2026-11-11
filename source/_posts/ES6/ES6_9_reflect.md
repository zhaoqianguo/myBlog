---
title: "ES6 学习笔记（1） - Reflect"
date: 2022-06-05 20:57:09
tags:
  - "ES6"
  - "es6"
categories: "ES6"
---

<h1 id="Reflect"><a href="#Reflect" class="headerlink" title="Reflect"></a>Reflect</h1><h2 id="1-概述"><a href="#1-概述" class="headerlink" title="1. 概述"></a>1. 概述</h2><p>Reflect 对象设计的目的：</p>
<ul>
<li>将<code>Object</code>对象的一些明显属于语言内部的方法（比如<code>Object.defineProperty</code>），放到<code>Reflect</code><br>对象上。</li>
<li>修改某些<code>Object</code>方法的返回结果，让其变得更合理。<code>Object.defineProperty(obj, name, desc)</code>在无法定义属性时，会抛出一个错误，而<code>Reflect.defineProperty(obj, name, desc)</code>则会返回<code>false</code>。</li>
<li>让<code>Object</code>操作都变成函数行为。某些<code>Object</code>操作是命令式，比如<code>name in obj</code>和<code>delete obj[name]</code>，而<code>Reflect.has(obj, name)</code>和<code>Reflect.deleteProperty(obj, name)</code>让它们变成了函数行为。</li>
<li><code>Reflect</code>对象的方法与<code>Proxy</code>对象的方法一一对应，只要是<code>Proxy</code>对象的方法，就能在<code>Reflect</code><br>对象上找到对应的方法。也就是说，不管<code>Proxy</code>怎么修改默认行为，你总可以在<code>Reflect</code>上获取默认行为。<figure class="highlight jsx"><table><tr><td class="gutter"><pre><span class="line">1</span><br><span class="line">2</span><br><span class="line">3</span><br><span class="line">4</span><br><span class="line">5</span><br><span class="line">6</span><br><span class="line">7</span><br><span class="line">8</span><br><span class="line">9</span><br></pre></td><td class="code"><pre><span class="line"><span class="title class_">Proxy</span>(target, &#123;</span><br><span class="line">  <span class="attr">set</span>: <span class="keyword">function</span> (<span class="params">target, name, value, receiver</span>) &#123;</span><br><span class="line">    <span class="keyword">var</span> success = <span class="title class_">Reflect</span>.<span class="title function_">set</span>(target, name, value, receiver);</span><br><span class="line">    <span class="keyword">if</span> (success) &#123;</span><br><span class="line">      <span class="variable language_">console</span>.<span class="title function_">log</span>(<span class="string">&#x27;property &#x27;</span> + name + <span class="string">&#x27; on &#x27;</span> + target + <span class="string">&#x27; set to &#x27;</span> + value);</span><br><span class="line">    &#125;</span><br><span class="line">    <span class="keyword">return</span> success;</span><br><span class="line">  &#125;,</span><br><span class="line">&#125;);</span><br></pre></td></tr></table></figure></li>
</ul>
<h2 id="2-静态方法"><a href="#2-静态方法" class="headerlink" title="2. 静态方法"></a>2. 静态方法</h2>

---
title: "《图解 HTTP》 学习笔记"
date: 2022-08-24 12:41:23
tags:
  - "HTTP"
  - "网络"
categories: "网络"
---

<h1 id="前言"><a href="#前言" class="headerlink" title="前言"></a>前言</h1><p>本书对互联网基盘——HTTP 协议进行了全面系统的介绍。作者由 HTTP 协议的发展历史娓娓道来，严谨细致地剖析了 HTTP 协议的结构，列举诸多常见通信场景及实战案例，最后延伸到 Web 安全、最新技术动向等方面。本书的特色为在讲解的同时，辅以大量生动形象的通信图例，更好地帮助读者深刻理解 HTTP 通信过程中客户端与服务器之间的交互情况。读者可通过本书快速了解并掌握 HTTP 协议的基础，前端工程师分析抓包数据，后端工程师实现 REST API、实现自己的 HTTP 服务器等过程中所需的 HTTP 相关知识点本书均有介绍。</p>
<p>本书适合 Web 开发工程师，以及对 HTTP 协议感兴趣的各层次读者。</p>
<h2 id="第一章、了解-WEB-及网络基础"><a href="#第一章、了解-WEB-及网络基础" class="headerlink" title="第一章、了解 WEB 及网络基础"></a>第一章、了解 WEB 及网络基础</h2><p><strong>HTTP 的诞生</strong></p>
<p>1989 年 3 月，HTTP 诞生了，最初设想的理念是：借助多文本之间互相关联形成的超文本，连成 WWW。</p>
<p><strong>Web 成长时代</strong></p>
<p>1990 年 11 月，CERN 研发了世界上第一台 WEB 服务器。</p>
<p>1990 年，大家针对 HTML1.0 草案进行讨论，因存在多处模糊的地方，草案被直接废弃。</p>
<p>1992 年 9 月，日本第一个<a target="_blank" rel="noopener" href="http://www.ibarakiken.gr.jp/www/">网站</a>的主页上线了。</p>
<p>1993 年 1 月，现代浏览器的祖先 <a target="_blank" rel="noopener" href="http://archive.ncsa.illinois.edu/mosaic.html">Mosaic</a> 问世，它以内联等形式显示 HTML 的图像，迅速在世界范围内流行开来。</p>
<p>1994 年 12 月，网景公司发布 Netscape Navigator 1.0。</p>
<p>1995 年，微软发布了 Internet Explorer 1.0 和 2.0。</p>
<p><strong>驻足不前的 HTTP</strong></p>
<p>HTTP 0.9 ：因为那时的 HTTP 并没有正式的标准被建立，所有含有 HTTP 1.0 之前版本的意思。</p>
<p>HTTP 1.0 ：1996 年 5 月正式作为标准被公布，并记载于 <a target="_blank" rel="noopener" href="https://www.ietf.org/rfc/rfc1945.txt">RFC1945</a>。</p>
<p>HTTP 1.1 ：1997 年 1 月公布，最新标准版本为 <a target="_blank" rel="noopener" href="https://www.ietf.org/rfc/rfc2616.txt">RFC2616</a>。</p>
<p><strong>网络基础 TCP&#x2F;IP</strong></p>
<p>通常使用的网络（包括互联网）是在 TCP&#x2F;IP 协议族的基础上运作的。而 HTTP 属于它内部的一个子集。</p>
<p><strong>TCP&#x2F;IP 协议族</strong></p>
<p>TCP&#x2F;IP 是互联网相关的各类协议族的总称。</p>
<p><strong>TCP&#x2F;IP 的分层管理</strong></p>
<p>分为四层：</p>
<ul>
<li>应用层：决定了向用户提供应用服务时通信的活动，例如：FTP、DNS、HTTP。</li>
<li>传输层：提供处于网络连接中的两台计算机之间的数据传输，TCP、UDP。</li>
<li>网络层：处理在网络上流动的数据包，规定传输路线。</li>
<li>数据链路层：处理连接网络的硬件部分。包括控制操作系统、硬件的设备驱动、网卡及光纤等物理可见部分。</li>
</ul>
<p>分层的好处：把各层之间的接口部分规划好后，修改某个地方时只需修改对应的层，每个层次内部不影响其他层。</p>
<p><strong>TCP&#x2F;IP 通信传输流</strong></p>
<p><img src="/../../assets/images/http/image.png" alt="alt text"></p>
<p>HTTP 举例：</p>
<p><img src="/../../assets/images/http/image1.png" alt="alt text"></p>
<p><strong>与 HTTP 关系密切的协议 : IP、TCP 和 DNS</strong></p>
<ul>
<li>负责传输的 IP 协议</li>
</ul>
<p><img src="/../../assets/images/http/image2.png" alt="alt text"></p>
<ul>
<li>确保可靠性的 TCP 协议</li>
</ul>
<p><img src="/../../assets/images/http/image3.png" alt="alt text"></p>
<ul>
<li>负责域名解析的 DNS 服务</li>
</ul>
<p><img src="/../../assets/images/http/image4.png" alt="alt text"></p>
<p><strong>各种协议与 HTTP 协议的关系</strong></p>
<p><img src="/../../assets/images/http/image5.png" alt="alt text"></p>
<h2 id="第二章、简单的-HTTP-协议"><a href="#第二章、简单的-HTTP-协议" class="headerlink" title="第二章、简单的 HTTP 协议"></a>第二章、简单的 HTTP 协议</h2><p>HTTP 协议用于客户端和服务器之间的通信，请求资源方成为客户端，提供资源响应方成为服务器端。</p>
<p>请求报文是由请求方法、请求 URI、协议版本、可选的请求首部字段和内容实体构成的。</p>
<p>请求报文的构成：</p>
<p><img src="/../../assets/images/http/image6.png" alt="alt text"></p>
<p>响应报文的构成：</p>
<p><img src="/../../assets/images/http/image7.png" alt="alt text"></p>
<p><strong>HTTP 是不保存状态的协议</strong></p>
<p>HTTP 是一个无状态协议，自身不具备保存之前发送过的请求或响应的功能。</p>
<p>之后随着发展，引入了 Cookie 技术。</p>
<p><strong>请求 URI 定位资源</strong></p>
<p>HTTP 协议使用 URI 定位互联网上的资源。正是因为 URI 的特定功能，在互联网上任意位置的资源都能访问到。</p>
<p><strong>告知服务器意图的 HTTP 方法</strong></p>
<p><img src="/../../assets/images/http/image8.png" alt="alt text"></p>
<p><strong>持久连接节省通信量</strong></p>
<p>HTTP 协议的初始版本中，每进行一次 HTTP 通信就要断开一次 TCP 连接。</p>
<p><strong>持久连接</strong></p>
<p>为解决上述 TCP 连接的问题，HTTP&#x2F;1.1 和一部分的 HTTP&#x2F;1.0 想出了持久连接的方法。</p>
<p>持久连接的特点是，只要任意一端没有明确提出断开连接，则保持 TCP 连接状态。</p>
<p>好处在于减少了 TCP 连接的重复建立和断开所造成的额外开销，减轻了服务器端的负载。</p>
<p><strong>管线化</strong></p>
<p>管线化技术出现后，能够做到同时并行发送多个请求，而不需要一个接一个地等待响应了。</p>
<p><strong>使用 Cookie 的状态管理</strong></p>
<p>Cookie 技术通过在请求和响应报文中写入 Cookie 信息来控制客户端的状态。</p>
<p>Cookie 会根据从服务器端发送的响应报文内的一个叫做 Set-Cookie 的首部字段信息，通知客户端保存 Cookie。当下次客户端再往该服务器发送请求时，客户端会自动在请求报文中加入 Cookie 值后发送出去。</p>
<p>服务器端发现客户端发送过来的 Cookie 后，会去检查究竟是从哪一个客户端发来的连接请求，然后对比服务器上的记录，最后得到之前的状态信息。</p>
<h2 id="第三章、HTTP-报文内的-HTTP-信息"><a href="#第三章、HTTP-报文内的-HTTP-信息" class="headerlink" title="第三章、HTTP 报文内的 HTTP 信息"></a>第三章、HTTP 报文内的 HTTP 信息</h2><p><strong>HTTP 报文</strong></p>
<p>用于 HTTP 协议交互的信息被称为 HTTP 报文。</p>
<p>HTTP 报文本身是由多行（用 CR+LF 作换行符）数据构成的字符串文本。</p>
<p>HTTP 报文大致可分为报文首部和报文主体两块，通常，并不一定要有报文主体。</p>
<p><img src="/../../assets/images/http/image9.png" alt="alt text"></p>
<p><strong>结构</strong></p>
<p><img src="/../../assets/images/http/image10.png" alt="alt text"></p>
<p><strong>实例</strong></p>
<p><img src="/../../assets/images/http/image11.png" alt="alt text"></p>
<p><strong>编码提升传输速率</strong></p>
<p>HTTP 在传输时可以原样直接传输，也可以在传输时通过编码提升传输速率，通过编码，能有效地处理大量的访问请求，但也消耗更多的 CPU 等资源。</p>
<p><strong>报文主体和实体主体的差异</strong></p>
<ul>
<li>报文：HTTP 通信中的基本单位，由 8 位组字节流组成，通过 HTTP 通信传输。</li>
<li>实体：作为请求或响应的有效载荷数据（补充项）被传输，其内容由实体首部和实体主体组成。</li>
</ul>
<p><strong>压缩传输的内容编码</strong></p>
<p>常用的内容编码有以下几种：</p>
<ul>
<li>gzip（GNU zip）</li>
<li>compress（UNIX 系统的标准压缩）</li>
<li>deflate（zlib）</li>
<li>identity（不进行编码）</li>
</ul>
<p><strong>分割发送的分块传输编码</strong></p>
<p>在传输大容量数据时，通过把数据分割成多块，能够让浏览器逐步显示页面，这种把实体主体分块的功能称为分块传输编码。</p>
<p>分块传输编码会将实体主体分成多个部分（块）。每一块都会用十六进制来标记块的大小，而实体主体的最后一块会使用“0(CR+LF)”来标记。</p>
<p><strong>发送多种数据的多部分对象集合</strong></p>
<p>发送的一份报文主体内可含有多类型实体。通常是在图片或文本文件等上传时使用。</p>
<p>多部分对象集合包含的对象如下：</p>
<ul>
<li>multipart&#x2F;form-data：在 Web 表单文件上传时使用。</li>
<li>multipart&#x2F;byteranges：状态码 206，响应报文包含了多个范围的内容时使用。</li>
</ul>
<p><strong>获取部分内容的范围请求</strong></p>
<p>为了解决加载超大图片导致网络中断的情况而实现的一种手段，叫做范围请求。</p>
<p>对一份 10 000 字节大小的资源，如果使用范围请求，可以只请求 5001~10 000 字节内的资源。</p>
<p><img src="/../../assets/images/http/image12.png" alt="alt text"></p>
<p><strong>内容协商返回最合适的内容</strong></p>
<p>当浏览器的默认语言为英语或中文，访问相同 URI 的 Web 页面时，则会显示对应的英语版或中文版的 Web 页面。这样的机制称为内容协商。</p>
<h2 id="第四章、返回结果的状态码"><a href="#第四章、返回结果的状态码" class="headerlink" title="第四章、返回结果的状态码"></a>第四章、返回结果的状态码</h2><p>HTTP 状态码负责表示客户端 HTTP 请求的返回结果、标记服务器端的处理是否正常、通知出现的错误等工作。</p>
<p><strong>状态码类别</strong>：</p>
<p><img src="/../../assets/images/http/image13.png" alt="alt text"></p>
<p>更多：<a target="_blank" rel="noopener" href="https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Status">HTTP 响应代码</a></p>
<h2 id="第五章、与-HTTP-协作的-Web-服务器"><a href="#第五章、与-HTTP-协作的-Web-服务器" class="headerlink" title="第五章、与 HTTP 协作的 Web 服务器"></a>第五章、与 HTTP 协作的 Web 服务器</h2><p><strong>用单台虚拟主机实现多个域名</strong></p>
<p>即便物理层面只有一台服务器，但只要使用虚拟主机的功能，则可以搭建多个站点。</p>
<p><strong>通信数据转发程序：代理、网关、隧道</strong></p>
<p>HTTP 通信时，除客户端和服务器以外，还有一些用于通信数据转发的应用程序：</p>
<ul>
<li><p>代理：一种有转发功能的应用程序，扮演了服务器和客户端中间人的角色。</p>
</li>
<li><p>网关：转发其他服务器通信数据的服务器，它就像自己拥有资源的源服务器一样对请求进行处理。</p>
</li>
<li><p>隧道：将相隔甚远的客户端和服务器两者之间进行中转，并保持双方通信连接的应用程序。</p>
<p><strong>保存资源的缓存</strong></p>
</li>
</ul>
<p>缓存是指代理服务器或客户端本地磁盘内保存的资源副本。利用缓存可减少对源服务器的访问，因此也就节省了通信流量和通信时间。</p>
<p><strong>客户端的缓存</strong></p>
<p>缓存不仅可以存在于缓存服务器内，还可以存在客户端浏览器中。以 Internet Explorer 程序为例，把客户端缓存称为临时网络文件。</p>
<h2 id="第六章、HTTP-首部"><a href="#第六章、HTTP-首部" class="headerlink" title="第六章、HTTP 首部"></a>第六章、HTTP 首部</h2><p><strong>注：这部分太多解释，建议看原文</strong></p>
<p><img src="/../../assets/images/http/image14.png" alt="alt text"></p>
<p><strong>HTTP 请求报文</strong></p>
<p>在请求中，HTTP 报文由方法、URI、HTTP 版本、HTTP 首部字段等部分构成</p>
<p><img src="/../../assets/images/http/image15.png" alt="alt text"></p>
<p><strong>HTTP 响应报文</strong></p>
<p>在响应中，HTTP 报文由 HTTP 版本、状态码（数字和原因短语）、HTTP 首部字段 3 部分构成。</p>
<p><img src="/../../assets/images/http/image16.png" alt="alt text"></p>
<p><strong>HTTP&#x2F;1.1 首部字段一览</strong></p>
<p>通用首部字段：</p>
<p><img src="/../../assets/images/http/image17.png" alt="alt text"></p>
<p>请求首部字段：</p>
<p><img src="/../../assets/images/http/image18.png" alt="alt text"></p>
<p>响应首部字段：</p>
<p><img src="/../../assets/images/http/image19.png" alt="alt text"></p>
<p>实体首部字段：</p>
<p><img src="/../../assets/images/http/image20.png" alt="alt text"></p>
<h2 id="第七章、HTTP-的缺点"><a href="#第七章、HTTP-的缺点" class="headerlink" title="第七章、HTTP 的缺点"></a>第七章、HTTP 的缺点</h2><p>主要的不足，例举如下：</p>
<ul>
<li>通信使用明文（不加密），内容可能会被窃听（例如：抓包）</li>
<li>不验证通信方的身份，因此有可能遭遇伪装（例如：DoS）</li>
<li>无法证明报文的完整性，所以有可能已遭篡改（例如：中间人攻击）</li>
</ul>
<p><strong>HTTP+ 加密 + 认证 + 完整性保护&#x3D;HTTPS</strong></p>
<p>为了统一解决上述这些问题，需要在 HTTP 等机制。我们把添加了加密及认证机制的称为 HTTPS。</p>
<p><strong>使用 HTTPS 通信</strong></p>
<p>经常会在 Web 的登录页面和购物结算界面等使用 HTTPS 通信。</p>
<p><strong>HTTPS 是身披 SSL 外壳的 HTTP</strong></p>
<p>HTTPS 并非是应用层的一种新协议。只是 HTTP 通信接口部分用 SSL 和 TLS 协议代替而已。</p>
<p>简言之，所谓 HTTPS，其实就是身披 SSL 协议这层外壳的 HTTP。</p>
<p><img src="/../../assets/images/http/image21.png" alt="alt text"></p>
<p>SSL 是独立于 HTTP 的协议，所以不光是 HTTP 协议，其他运行在应用层的 SMTP 和 Telnet 等协议均可配合 SSL 协议使用。可以说 SSL 是当今世界上应用最为广泛的网络安全技术。</p>
<p><strong>相互交换密钥的公开密钥加密技术</strong></p>
<p>SSL 采用一种叫做公开密钥加密（非对称加密）的加密处理方式。</p>
<p><strong>HTTPS 的安全通信机制</strong></p>
<p>通信步骤：</p>
<p><img src="/../../assets/images/http/image22.png" alt="alt text"></p>
<p><strong>SSL 速度慢吗</strong></p>
<p>HTTPS 也存在一些问题，那就是当使用 SSL 时，它的处理速度会变慢。</p>
<p>HTTPS 比 HTTP 要慢 2 到 100 倍，因为与纯文本通信相比，加密通信会消耗更多的 CPU 及内存资源。如果每次通信都加密，会消耗相当多的资源，平摊到一台计算机上时，能够处理的请求数量必定也会随之减少。</p>
<h2 id="第八章、确认访问用户身份的认证"><a href="#第八章、确认访问用户身份的认证" class="headerlink" title="第八章、确认访问用户身份的认证"></a>第八章、确认访问用户身份的认证</h2><p><strong>何为认证</strong></p>
<p>服务器为了确认用户的身份，通常需要核对一些信息：</p>
<ul>
<li>密码</li>
<li>动态令牌</li>
<li>数字证书</li>
<li>生物认证</li>
<li>IC 卡</li>
</ul>
<p><strong>HTTP 使用的认证方式</strong></p>
<ul>
<li>BASIC 认证（基本认证）</li>
<li>DIGEST 认证（摘要认证）</li>
<li>SSL 客户端认证</li>
<li>FormBase 认证（基于表单认证）</li>
</ul>
<h2 id="第九章、基于-HTTP-的功能追加协议"><a href="#第九章、基于-HTTP-的功能追加协议" class="headerlink" title="第九章、基于 HTTP 的功能追加协议"></a>第九章、基于 HTTP 的功能追加协议</h2><p><strong>消除 HTTP 瓶颈的 SPDY</strong></p>
<p>Google 在 2010 年发布了 <a target="_blank" rel="noopener" href="http://www.chromium.org/spdy/">SPDY</a>（取自 SPeeDY，发音同 speedy），其开发目标旨在解决 HTTP 的性能瓶颈，缩短 Web 页面的加载时间（50%）。</p>
<p><strong>SPDY 的目标</strong></p>
<p>陆续出现的 Ajax 和 Comet 等提高易用性的技术，一定程度上使 HTTP 得到了改善，但 HTTP 协议本身的限制也令人有些束手无策。为了进行根本性的改善，需要有一些协议层面上的改动。</p>
<p>处于持续开发状态中的 SPDY 协议，正是为了在协议级别消除 HTTP 所遭遇的瓶颈。</p>
<p>使用 SPDY 后，HTTP 协议额外获得以下功能。</p>
<ul>
<li>多路复用流：通过单一的 TCP 连接，可以无限制处理多个 HTTP 请求。</li>
<li>赋予请求优先级：可以给请求逐个分配优先级顺序。这样主要是为了在发送多个请求时，解决因带宽低而导致响应变慢的问题。</li>
<li>压缩 HTTP 首部</li>
<li>推送功能：支持服务器主动向客户端推送数据的功能。</li>
<li>服务器提示功能：服务器可以主动提示客户端请求所需的资源。</li>
</ul>
<p><strong>使用浏览器进行全双工通信的 WebSocket</strong></p>
<p>利用 Ajax 和 Comet 技术进行通信可以提升 Web 的浏览速度。但问题在于通信若使用 HTTP 协议，就无法彻底解决瓶颈问题。WebSocket 网络技术正是为解决这些问题而实现的一套新协议及 API。</p>
<p><strong>WebSocket 协议</strong></p>
<p>主要特点：</p>
<ul>
<li>推送功能：支持由服务器向客户端推送数据的推送功能。</li>
<li>减少通信量：只要建立起 WebSocket 连接，就希望一直保持连接状态。</li>
</ul>
<p><strong>期盼已久的 HTTP&#x2F;2.0</strong></p>
<p>特点：</p>
<p><img src="/../../assets/images/http/image23.png" alt="alt text"></p>
<p><strong>Web 服务器管理文件的 WebDAV</strong></p>
<p>WebDAV（基于万维网的分布式创作和版本控制）是一个可对 Web 服务器上的内容直接进行文件复制、编辑等操作的分布式文件系统。</p>
<h2 id="第十章、构建-Web-内容的技术"><a href="#第十章、构建-Web-内容的技术" class="headerlink" title="第十章、构建 Web 内容的技术"></a>第十章、构建 Web 内容的技术</h2><ul>
<li>HTML</li>
<li>CSS</li>
<li>JavaScript</li>
<li>动态 HTML</li>
<li>CGI</li>
<li>Servlet</li>
<li>XML</li>
<li>RSS&#x2F;Atom</li>
<li>JSON</li>
</ul>
<h2 id="第十一章、Web-的攻击技术"><a href="#第十一章、Web-的攻击技术" class="headerlink" title="第十一章、Web 的攻击技术"></a>第十一章、Web 的攻击技术</h2><p>对 Web 应用的攻击模式有以下两种：</p>
<ul>
<li>主动攻击：是指攻击者通过直接访问 Web 应用，把攻击代码传入的攻击模式</li>
<li>被动攻击：指利用圈套策略执行攻击代码的攻击模式</li>
</ul>
<p><strong>因输出值转义不完全引发的安全漏洞：</strong></p>
<ul>
<li><p>XSS 注入</p>
</li>
<li><p>SQL 注入</p>
</li>
<li><p>OS 命令注入</p>
</li>
<li><p>HTTP 首部注入攻击</p>
</li>
<li><p>邮件首部注入攻击</p>
</li>
<li><p>目录遍历攻击</p>
</li>
<li><p>远程文件包含漏洞</p>
<p><strong>因设置或设计上的缺陷引发的安全漏洞：</strong></p>
</li>
<li><p>强制浏览</p>
</li>
<li><p>不正确的错误信息处理</p>
</li>
<li><p>开放重定向</p>
</li>
</ul>
<p><strong>因会话管理疏忽引发的安全漏洞：</strong></p>
<ul>
<li>会话劫持</li>
<li>会话固定攻击</li>
<li>跨站点请求伪造</li>
</ul>
<p><strong>其他安全漏洞：</strong></p>
<ul>
<li>密码破解</li>
<li>点击劫持</li>
<li>DoS 攻击</li>
<li>后门程序</li>
</ul>

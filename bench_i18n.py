"""
Translations for round 2 (CC0, written for this repository).

TICKETS_I18N: the eight round-1 tickets in seven more languages, same meaning,
same facts (amounts, days, product names), so an answer that changes with the
language is a language effect, not a content effect.

PARAGRAPH: one ~600-character support email in eight languages. With the eight
tickets it gives nine texts per language of different lengths, regressed to
estimate billed tokens per character in each script.
"""

LANGS = ["en", "zh", "ja", "ko", "es", "hi", "ar", "ru"]

TICKETS_I18N: dict[str, dict[str, str]] = {
    "t01": {
        "zh": "我三月份的账单被扣了两次款。请今天把重复的那笔退给我，我的信用卡快到额度上限了。",
        "ja": "3月分の請求が二重に引き落とされました。重複分を今日中に返金してください。カードの利用限度額に近づいています。",
        "ko": "3월 청구서가 두 번 결제되었습니다. 중복 결제된 금액을 오늘 환불해 주세요. 카드 한도가 거의 다 찼습니다.",
        "es": "Me cobraron dos veces la factura de marzo. Por favor, reembolsen hoy el cargo duplicado; mi tarjeta está cerca de su límite.",
        "hi": "मार्च के इनवॉइस के लिए मुझसे दो बार पैसे काटे गए। कृपया आज ही डुप्लिकेट चार्ज वापस करें, मेरा कार्ड अपनी सीमा के करीब है।",
        "ar": "تم خصم فاتورة شهر مارس مرتين. يرجى استرداد المبلغ المكرر اليوم، فبطاقتي قريبة من حدها الأقصى.",
        "ru": "С меня дважды списали оплату за мартовский счёт. Пожалуйста, верните повторное списание сегодня — лимит моей карты почти исчерпан.",
    },
    "t02": {
        "zh": "自从昨天更新后，导出 CSV 的按钮就一直在转圈。我们周五开董事会需要这份报告。",
        "ja": "昨日のアップデート以降、CSVエクスポートボタンがずっと読み込み中のままです。金曜日の取締役会でこのレポートが必要です。",
        "ko": "어제 업데이트 이후로 CSV 내보내기 버튼이 계속 로딩만 됩니다. 금요일 이사회 회의에 이 보고서가 필요합니다.",
        "es": "El botón de exportar a CSV no deja de cargar desde la actualización de ayer. Necesitamos el informe para una reunión del consejo el viernes.",
        "hi": "कल के अपडेट के बाद से CSV एक्सपोर्ट बटन लगातार घूम रहा है। शुक्रवार की बोर्ड मीटिंग के लिए हमें यह रिपोर्ट चाहिए।",
        "ar": "زر التصدير إلى CSV لا يتوقف عن التحميل منذ تحديث الأمس. نحتاج التقرير لاجتماع مجلس الإدارة يوم الجمعة.",
        "ru": "После вчерашнего обновления кнопка экспорта в CSV бесконечно крутится. Нам нужен отчёт к заседанию совета директоров в пятницу.",
    },
    "t03": {
        "zh": "我可以在计费周期中途从 Team 套餐升级到 Business 吗？会按比例计费吗？另外你们有年付折扣吗？",
        "ja": "請求期間の途中でTeamプランからBusinessプランにアップグレードできますか？日割りで請求されますか？また、年払いの割引はありますか？",
        "ko": "결제 주기 중간에 Team 요금제에서 Business로 업그레이드할 수 있나요? 일할 계산으로 청구되나요? 그리고 연간 결제 할인이 있나요?",
        "es": "¿Puedo pasar del plan Team al plan Business a mitad de ciclo, y se me cobrará de forma prorrateada? ¿Ofrecen también descuentos anuales?",
        "hi": "क्या मैं बिलिंग साइकिल के बीच में Team प्लान से Business में अपग्रेड कर सकता हूँ, और क्या बिल आनुपातिक रूप से लगेगा? क्या आप सालाना छूट भी देते हैं?",
        "ar": "هل يمكنني الترقية من خطة Team إلى Business في منتصف الدورة، وهل ستتم الفوترة بشكل تناسبي؟ وهل تقدمون خصومات سنوية؟",
        "ru": "Можно ли перейти с тарифа Team на Business в середине расчётного периода, и будет ли оплата пропорциональной? И есть ли у вас скидки при оплате за год?",
    },
    "t04": {
        "zh": "从今天早上开始，你们的 API 大约每十个请求就有一个返回 500 错误。我们的结账流程依赖它，现在正在让我们损失销售额。",
        "ja": "今朝から、御社のAPIがおよそ10回に1回500エラーを返しています。当社の決済はこれに依存しており、今まさに売上を失っています。",
        "ko": "오늘 아침부터 귀사의 API가 요청 10건 중 약 1건꼴로 500 오류를 반환합니다. 저희 결제가 이 API에 의존하고 있어서 지금 매출 손실이 발생하고 있습니다.",
        "es": "Desde esta mañana su API devuelve errores 500 en aproximadamente una de cada diez solicitudes. Nuestro proceso de pago depende de ella. Esto nos está costando ventas ahora mismo.",
        "hi": "आज सुबह से आपका API लगभग हर दस में से एक अनुरोध पर 500 एरर दे रहा है। हमारा चेकआउट इसी पर निर्भर है। इससे अभी हमारी बिक्री का नुकसान हो रहा है।",
        "ar": "منذ صباح اليوم تُرجع واجهة API الخاصة بكم أخطاء 500 في طلب واحد تقريبًا من كل عشرة. عملية الدفع لدينا تعتمد عليها، وهذا يكلفنا مبيعات الآن.",
        "ru": "С сегодняшнего утра ваш API возвращает ошибку 500 примерно на каждый десятый запрос. От него зависит наша оплата заказов. Прямо сейчас мы теряем продажи.",
    },
    "t05": {
        "zh": "说实话我在考虑换到竞争对手那边。他们更便宜的套餐就提供 SSO，而你们的客服上次隔了四天才回复。",
        "ja": "正直、競合他社への乗り換えを考えています。あちらは安いプランでもSSOを提供していますし、前回御社のサポートは返信に4日かかりました。",
        "ko": "솔직히 경쟁사로 옮길까 생각 중입니다. 그쪽은 더 저렴한 요금제에서도 SSO를 제공하고, 지난번 귀사 지원팀은 답변하는 데 4일이나 걸렸습니다.",
        "es": "Sinceramente, estoy pensando en irme a la competencia. Ofrecen SSO en el plan más barato y la última vez su soporte tardó cuatro días en responder.",
        "hi": "सच कहूँ तो मैं किसी प्रतिस्पर्धी के पास जाने की सोच रहा हूँ। वे सस्ते प्लान में भी SSO देते हैं और पिछली बार आपके सपोर्ट को जवाब देने में चार दिन लगे।",
        "ar": "بصراحة أفكر في الانتقال إلى منافس. إنهم يقدمون تسجيل الدخول الموحد SSO في الخطة الأرخص، وقد استغرق دعمكم أربعة أيام للرد في المرة الماضية.",
        "ru": "Честно говоря, подумываю перейти к конкуренту. У них SSO есть даже в более дешёвом тарифе, а ваша поддержка в прошлый раз отвечала четыре дня.",
    },
    "t06": {
        "zh": "只是想说新的仪表盘很棒，谢谢。有个小问题：深色模式开关不会记住我的选择。",
        "ja": "新しいダッシュボードがとても良いとお伝えしたくて。ありがとうございます。一点だけ、ダークモードの切り替えが私の選択を記憶しません。",
        "ko": "새 대시보드가 정말 좋다는 말씀을 드리고 싶었어요. 감사합니다. 사소한 문제가 하나 있는데, 다크 모드 토글이 제 선택을 기억하지 않습니다.",
        "es": "Solo quería decir que el nuevo panel es genial, gracias. Un detalle: el interruptor del modo oscuro no recuerda mi elección.",
        "hi": "बस इतना कहना था कि नया डैशबोर्ड बहुत बढ़िया है, धन्यवाद। एक छोटी सी बात: डार्क मोड टॉगल मेरी पसंद याद नहीं रखता।",
        "ar": "أردت فقط أن أقول إن لوحة التحكم الجديدة رائعة، شكرًا. ملاحظة صغيرة: مفتاح الوضع الداكن لا يتذكر اختياري.",
        "ru": "Просто хотел сказать, что новая панель отличная, спасибо. Мелочь: переключатель тёмной темы не запоминает мой выбор.",
    },
    "t07": {
        "zh": "我上个月已经取消了订阅，但 3 号还是被扣了款。我要把这笔钱退回来，并且确认以后不会再发生。",
        "ja": "先月サブスクリプションを解約したのに、3日にまた請求されました。その代金を返金し、二度と起きないことを確認してください。",
        "ko": "지난달에 구독을 해지했는데 3일에 또 요금이 청구되었습니다. 그 금액을 환불받고 다시는 이런 일이 없을 거라는 확인을 받고 싶습니다.",
        "es": "Cancelé mi suscripción el mes pasado pero aun así me cobraron el día 3. Quiero que me devuelvan ese dinero y confirmación de que no volverá a pasar.",
        "hi": "मैंने पिछले महीने अपनी सदस्यता रद्द कर दी थी, फिर भी 3 तारीख को मुझसे पैसे काटे गए। मुझे वह पैसा वापस चाहिए और यह पुष्टि कि ऐसा दोबारा नहीं होगा।",
        "ar": "ألغيت اشتراكي الشهر الماضي لكن تم خصم المبلغ مني في اليوم الثالث. أريد استرداد هذا المال وتأكيدًا بأن ذلك لن يتكرر.",
        "ru": "Я отменил подписку в прошлом месяце, но 3-го числа с меня всё равно списали деньги. Я хочу вернуть эти деньги и получить подтверждение, что это не повторится.",
    },
    "t08": {
        "zh": "我怎样给我们的工作区添加第二个管理员？设置页面只显示了所有者，我找不到邀请的选项。",
        "ja": "ワークスペースに2人目の管理者を追加するにはどうすればいいですか？設定ページにはオーナーしか表示されず、招待のオプションが見つかりません。",
        "ko": "워크스페이스에 두 번째 관리자를 어떻게 추가하나요? 설정 페이지에는 소유자만 표시되고 초대 옵션을 찾을 수 없습니다.",
        "es": "¿Cómo añado un segundo administrador a nuestro espacio de trabajo? La página de configuración solo muestra al propietario y no encuentro la opción de invitar.",
        "hi": "मैं अपने वर्कस्पेस में दूसरा एडमिन कैसे जोड़ूँ? सेटिंग्स पेज पर सिर्फ़ ओनर दिखता है और मुझे इनवाइट का विकल्प नहीं मिल रहा।",
        "ar": "كيف أضيف مسؤولًا ثانيًا إلى مساحة العمل الخاصة بنا؟ صفحة الإعدادات لا تعرض سوى المالك ولا أجد خيار الدعوة.",
        "ru": "Как добавить второго администратора в наше рабочее пространство? На странице настроек отображается только владелец, и я не могу найти опцию приглашения.",
    },
}

PARAGRAPH: dict[str, str] = {
    "en": "Hello, I am writing about our team account. Last week three of our five seats stopped receiving the monthly usage report, and the invoice for September shows a charge we do not recognise. We changed our billing email in August, so the reports may be going to the old address. Could you confirm which address is on file, resend the September report to the finance mailbox, and explain the extra charge of 49 dollars? If it was added by mistake, please refund it to the original card. We would also like to know whether we can switch to annual billing before the next renewal date.",
    "zh": "您好，我想咨询我们团队账户的问题。上周我们五个席位中有三个不再收到每月使用报告，而且九月的账单上有一笔我们不认识的费用。我们在八月更换了账单邮箱，所以报告可能还在发往旧地址。能否确认一下系统里登记的是哪个地址，把九月的报告重新发送到财务邮箱，并解释一下那笔额外的四十九美元费用？如果是误加的，请退回到原来的银行卡。我们还想知道能否在下次续费日期之前改为按年付费。",
    "ja": "こんにちは、チームアカウントについてご連絡します。先週、5席のうち3席で月次利用レポートが届かなくなり、9月の請求書には心当たりのない料金が記載されています。8月に請求先のメールアドレスを変更したため、レポートが古いアドレスに送られているのかもしれません。登録されているアドレスをご確認のうえ、9月のレポートを経理用のメールボックスに再送し、49ドルの追加料金について説明していただけますか。誤って追加されたものであれば、元のカードに返金してください。また、次回の更新日より前に年払いへ切り替えられるかも教えてください。",
    "ko": "안녕하세요, 저희 팀 계정 관련해서 문의드립니다. 지난주에 좌석 다섯 개 중 세 개가 월간 사용 보고서를 받지 못하게 되었고, 9월 청구서에는 저희가 알지 못하는 요금이 있습니다. 8월에 청구용 이메일을 변경했기 때문에 보고서가 이전 주소로 가고 있을 수도 있습니다. 등록된 주소가 어느 것인지 확인해 주시고, 9월 보고서를 재무팀 메일함으로 다시 보내 주시며, 49달러의 추가 요금에 대해 설명해 주실 수 있을까요? 실수로 추가된 것이라면 원래 카드로 환불해 주세요. 또한 다음 갱신일 전에 연간 결제로 전환할 수 있는지도 알고 싶습니다.",
    "es": "Hola, les escribo sobre la cuenta de nuestro equipo. La semana pasada, tres de nuestras cinco licencias dejaron de recibir el informe mensual de uso, y la factura de septiembre muestra un cargo que no reconocemos. Cambiamos nuestro correo de facturación en agosto, así que es posible que los informes lleguen a la dirección antigua. ¿Podrían confirmar qué dirección tienen registrada, reenviar el informe de septiembre al buzón de finanzas y explicar el cargo adicional de 49 dólares? Si se añadió por error, reembólsenlo a la tarjeta original. También nos gustaría saber si podemos pasar a facturación anual antes de la próxima fecha de renovación.",
    "hi": "नमस्ते, मैं हमारी टीम के अकाउंट के बारे में लिख रहा हूँ। पिछले हफ़्ते हमारी पाँच में से तीन सीटों पर मासिक उपयोग रिपोर्ट आना बंद हो गई, और सितंबर के इनवॉइस में एक ऐसा चार्ज दिख रहा है जिसे हम नहीं पहचानते। हमने अगस्त में अपना बिलिंग ईमेल बदला था, इसलिए हो सकता है रिपोर्ट पुराने पते पर जा रही हों। क्या आप पुष्टि कर सकते हैं कि रिकॉर्ड में कौन सा पता दर्ज है, सितंबर की रिपोर्ट फ़ाइनेंस मेलबॉक्स पर दोबारा भेज सकते हैं, और 49 डॉलर के अतिरिक्त चार्ज के बारे में बता सकते हैं? अगर यह गलती से जुड़ा है, तो कृपया इसे मूल कार्ड पर वापस कर दें। हम यह भी जानना चाहते हैं कि क्या अगली रिन्यूअल तारीख से पहले हम सालाना बिलिंग पर जा सकते हैं।",
    "ar": "مرحبًا، أكتب إليكم بخصوص حساب فريقنا. في الأسبوع الماضي توقفت ثلاثة من مقاعدنا الخمسة عن تلقي تقرير الاستخدام الشهري، وتظهر فاتورة سبتمبر رسومًا لا نعرفها. لقد غيّرنا بريد الفوترة الإلكتروني في أغسطس، لذا قد تكون التقارير تُرسل إلى العنوان القديم. هل يمكنكم تأكيد العنوان المسجل لديكم، وإعادة إرسال تقرير سبتمبر إلى صندوق بريد المالية، وتوضيح الرسوم الإضافية البالغة 49 دولارًا؟ إذا أُضيفت عن طريق الخطأ، يرجى استردادها إلى البطاقة الأصلية. ونود أيضًا معرفة ما إذا كان بإمكاننا التحويل إلى الفوترة السنوية قبل تاريخ التجديد القادم.",
    "ru": "Здравствуйте, пишу по поводу аккаунта нашей команды. На прошлой неделе три из пяти наших мест перестали получать ежемесячный отчёт об использовании, а в счёте за сентябрь есть списание, которое мы не узнаём. В августе мы сменили адрес электронной почты для счетов, поэтому отчёты, возможно, уходят на старый адрес. Не могли бы вы подтвердить, какой адрес указан в системе, повторно отправить сентябрьский отчёт на почту финансового отдела и объяснить дополнительное списание в 49 долларов? Если оно было добавлено по ошибке, верните его на исходную карту. Мы также хотели бы узнать, можно ли перейти на годовую оплату до следующей даты продления.",
}


# The round-1 questions in each language: instructions, Choice option
# descriptions and Score anchors are translated; Choice option KEYS stay in
# English so answers map back to the same canonical option in every arm.
# (`sentiment` has no descriptions in English, so only its instruction moves.)
QUESTIONS_I18N: dict[str, dict[str, dict]] = {
    "zh": {
        "is_billing": {"instructions": "这张新工单是否与账单、扣费或退款有关？"},
        "department": {"instructions": "哪个团队应该处理这张新工单？", "criteria": {"billing": "付款、发票、退款、套餐变更", "technical": "缺陷、错误、服务中断、集成", "account": "用户、权限、设置", "feedback": "表扬或建议，无需处理"}},
        "urgency": {"instructions": "这张新工单有多紧急？", "criteria": ["可以等一周", "本周内处理", "今天处理", "一小时内处理"]},
        "wants_refund": {"instructions": "客户是否要求退钱？"},
        "sentiment": {"instructions": "这张新工单中客户的语气是什么？"},
        "churn_risk": {"instructions": "根据这张新工单，这位客户取消订阅的可能性有多大？", "criteria": ["不太可能", "有可能", "很可能"]},
        "mentions_competitor": {"instructions": "客户是否提到要转向竞争对手或与竞争对手比较？"},
        "production_impact": {"instructions": "客户自己的生产系统或收入现在是否受到影响？"},
    },
    "ja": {
        "is_billing": {"instructions": "この新しいチケットは請求、課金、または返金に関するものですか？"},
        "department": {"instructions": "この新しいチケットはどのチームが対応すべきですか？", "criteria": {"billing": "支払い、請求書、返金、プラン変更", "technical": "バグ、エラー、障害、連携", "account": "ユーザー、権限、設定", "feedback": "対応不要の称賛や提案"}},
        "urgency": {"instructions": "この新しいチケットの緊急度はどのくらいですか？", "criteria": ["1週間待てる", "今週中に対応", "今日中に対応", "1時間以内に対応"]},
        "wants_refund": {"instructions": "顧客は返金を求めていますか？"},
        "sentiment": {"instructions": "この新しいチケットでの顧客の口調はどうですか？"},
        "churn_risk": {"instructions": "この新しいチケットから判断して、この顧客が解約する可能性はどのくらいですか？", "criteria": ["可能性は低い", "可能性はある", "可能性が高い"]},
        "mentions_competitor": {"instructions": "顧客は競合他社への乗り換えや比較に言及していますか？"},
        "production_impact": {"instructions": "顧客自身の本番システムや売上は今まさに影響を受けていますか？"},
    },
    "ko": {
        "is_billing": {"instructions": "이 새 티켓은 청구, 결제 또는 환불에 관한 것입니까?"},
        "department": {"instructions": "이 새 티켓은 어느 팀이 처리해야 합니까?", "criteria": {"billing": "결제, 청구서, 환불, 요금제 변경", "technical": "버그, 오류, 장애, 연동", "account": "사용자, 권한, 설정", "feedback": "조치가 필요 없는 칭찬이나 제안"}},
        "urgency": {"instructions": "이 새 티켓은 얼마나 긴급합니까?", "criteria": ["일주일 기다릴 수 있음", "이번 주 내 처리", "오늘 처리", "한 시간 내 처리"]},
        "wants_refund": {"instructions": "고객이 환불을 요청합니까?"},
        "sentiment": {"instructions": "이 새 티켓에서 고객의 어조는 어떻습니까?"},
        "churn_risk": {"instructions": "이 새 티켓을 바탕으로 볼 때, 이 고객이 해지할 가능성은 얼마나 됩니까?", "criteria": ["가능성 낮음", "가능성 있음", "가능성 높음"]},
        "mentions_competitor": {"instructions": "고객이 경쟁사로 옮기거나 경쟁사와 비교하는 것을 언급합니까?"},
        "production_impact": {"instructions": "고객 자신의 운영 시스템이나 매출이 지금 영향을 받고 있습니까?"},
    },
    "es": {
        "is_billing": {"instructions": "¿El nuevo ticket trata sobre facturación, cargos o reembolsos?"},
        "department": {"instructions": "¿Qué equipo debe encargarse del nuevo ticket?", "criteria": {"billing": "Pagos, facturas, reembolsos, cambios de plan", "technical": "Errores, fallos, caídas del servicio, integraciones", "account": "Usuarios, permisos, configuración", "feedback": "Elogios o sugerencias que no requieren acción"}},
        "urgency": {"instructions": "¿Qué tan urgente es el nuevo ticket?", "criteria": ["Puede esperar una semana", "Atender esta semana", "Atender hoy", "Atender en la próxima hora"]},
        "wants_refund": {"instructions": "¿El cliente pide que le devuelvan el dinero?"},
        "sentiment": {"instructions": "¿Cuál es el tono del cliente en el nuevo ticket?"},
        "churn_risk": {"instructions": "Según el nuevo ticket, ¿qué probabilidad hay de que este cliente cancele?", "criteria": ["Improbable", "Posible", "Probable"]},
        "mentions_competitor": {"instructions": "¿El cliente menciona cambiarse a un competidor o compararse con uno?"},
        "production_impact": {"instructions": "¿El sistema de producción o los ingresos del propio cliente están afectados ahora mismo?"},
    },
    "hi": {
        "is_billing": {"instructions": "क्या नया टिकट बिलिंग, चार्ज या रिफ़ंड के बारे में है?"},
        "department": {"instructions": "नए टिकट को कौन सी टीम संभाले?", "criteria": {"billing": "भुगतान, इनवॉइस, रिफ़ंड, प्लान बदलाव", "technical": "बग, एरर, आउटेज, इंटीग्रेशन", "account": "यूज़र, अनुमतियाँ, सेटिंग्स", "feedback": "तारीफ़ या सुझाव, जिन पर कोई कार्रवाई ज़रूरी नहीं"}},
        "urgency": {"instructions": "नया टिकट कितना ज़रूरी है?", "criteria": ["एक हफ़्ता रुक सकता है", "इस हफ़्ते निपटाएँ", "आज निपटाएँ", "एक घंटे के भीतर निपटाएँ"]},
        "wants_refund": {"instructions": "क्या ग्राहक पैसे वापस माँग रहा है?"},
        "sentiment": {"instructions": "नए टिकट में ग्राहक का लहजा कैसा है?"},
        "churn_risk": {"instructions": "नए टिकट के आधार पर, इस ग्राहक के सदस्यता रद्द करने की कितनी संभावना है?", "criteria": ["संभावना कम", "संभव", "संभावना ज़्यादा"]},
        "mentions_competitor": {"instructions": "क्या ग्राहक किसी प्रतिस्पर्धी के पास जाने या उससे तुलना करने का ज़िक्र करता है?"},
        "production_impact": {"instructions": "क्या ग्राहक का अपना प्रोडक्शन सिस्टम या राजस्व अभी प्रभावित है?"},
    },
    "ar": {
        "is_billing": {"instructions": "هل تتعلق التذكرة الجديدة بالفوترة أو الرسوم أو الاسترداد؟"},
        "department": {"instructions": "أي فريق يجب أن يتولى التذكرة الجديدة؟", "criteria": {"billing": "المدفوعات، الفواتير، المبالغ المستردة، تغييرات الخطة", "technical": "الأعطال، الأخطاء، انقطاع الخدمة، التكاملات", "account": "المستخدمون، الصلاحيات، الإعدادات", "feedback": "ثناء أو اقتراحات لا تتطلب إجراء"}},
        "urgency": {"instructions": "ما مدى إلحاح التذكرة الجديدة؟", "criteria": ["يمكن أن تنتظر أسبوعًا", "تُعالج هذا الأسبوع", "تُعالج اليوم", "تُعالج خلال ساعة"]},
        "wants_refund": {"instructions": "هل يطلب العميل استرداد أمواله؟"},
        "sentiment": {"instructions": "ما نبرة العميل في التذكرة الجديدة؟"},
        "churn_risk": {"instructions": "بناءً على التذكرة الجديدة، ما مدى احتمال أن يلغي هذا العميل اشتراكه؟", "criteria": ["غير مرجح", "محتمل", "مرجح"]},
        "mentions_competitor": {"instructions": "هل يذكر العميل الانتقال إلى منافس أو المقارنة به؟"},
        "production_impact": {"instructions": "هل يتأثر نظام الإنتاج أو الإيرادات الخاصة بالعميل الآن؟"},
    },
    "ru": {
        "is_billing": {"instructions": "Касается ли новый тикет счетов, списаний или возвратов?"},
        "department": {"instructions": "Какая команда должна заняться новым тикетом?", "criteria": {"billing": "Платежи, счета, возвраты, смена тарифа", "technical": "Баги, ошибки, сбои, интеграции", "account": "Пользователи, права доступа, настройки", "feedback": "Похвала или предложения без необходимости действий"}},
        "urgency": {"instructions": "Насколько срочен новый тикет?", "criteria": ["Может подождать неделю", "Решить на этой неделе", "Решить сегодня", "Решить в течение часа"]},
        "wants_refund": {"instructions": "Просит ли клиент вернуть деньги?"},
        "sentiment": {"instructions": "Какой тон у клиента в новом тикете?"},
        "churn_risk": {"instructions": "Судя по новому тикету, насколько вероятно, что этот клиент откажется от подписки?", "criteria": ["Маловероятно", "Возможно", "Вероятно"]},
        "mentions_competitor": {"instructions": "Упоминает ли клиент переход к конкуренту или сравнение с ним?"},
        "production_impact": {"instructions": "Затронуты ли прямо сейчас рабочая система или выручка самого клиента?"},
    },
}

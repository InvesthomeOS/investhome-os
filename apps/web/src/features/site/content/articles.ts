export type SiteArticleCategory =
  | 'guides'
  | 'market'
  | 'investment'
  | 'tax'
  | 'product';

export type SiteArticle = {
  slug: string;
  title: { en: string; tr: string };
  excerpt: { en: string; tr: string };
  body: { en: string[]; tr: string[] };
  category: SiteArticleCategory;
  tags: string[];
  author: { name: string; role: { en: string; tr: string } };
  publishedAt: string;
  readingMinutes: number;
  relatedSlugs: string[];
  seo: {
    title: { en: string; tr: string };
    description: { en: string; tr: string };
  };
  /** AI workflow fields — draft/review/publish prep (no autonomous publish). */
  workflow: {
    status: 'published' | 'human_review' | 'ai_draft';
    aiDraftAvailable: boolean;
    internalLinks: string[];
  };
};

export const SITE_ARTICLE_CATEGORIES: {
  id: SiteArticleCategory;
  label: { en: string; tr: string };
}[] = [
  { id: 'guides', label: { en: 'Guides', tr: 'Rehberler' } },
  { id: 'market', label: { en: 'Market', tr: 'Piyasa' } },
  { id: 'investment', label: { en: 'Investment', tr: 'Yatırım' } },
  { id: 'tax', label: { en: 'Tax & Structure', tr: 'Vergi & Yapı' } },
  { id: 'product', label: { en: 'Product', tr: 'Ürün' } },
];

/**
 * Content-layer seed articles. Ready to swap for Marketing Content Studio / CMS
 * when public published-content APIs are exposed.
 */
export const SITE_ARTICLES: SiteArticle[] = [
  {
    slug: 'first-time-investor-checklist',
    title: {
      en: 'First-time investor checklist for Turkish real estate',
      tr: 'Türkiye gayrimenkulünde ilk yatırımcı kontrol listesi',
    },
    excerpt: {
      en: 'A practical sequence from intent to due diligence, financing, and handoff.',
      tr: 'Niyetten due diligence, finansman ve teslime pratik bir sıra.',
    },
    body: {
      en: [
        'Clarify your objective: yield, appreciation, lifestyle, or a blend.',
        'Map ticket size, currency exposure, and hold period before touring inventory.',
        'Request audited track record, delivery history, and rental assumptions in writing.',
        'Stress-test cash flow with vacancy, opex, and rate scenarios using the calculators.',
        'Only then book a consultation — bring your model outputs and open questions.',
      ],
      tr: [
        'Hedefinizi netleştirin: getiri, değer artışı, yaşam tarzı veya bir karışım.',
        'Envanteri gezmeden önce bütçe, kur riski ve elde tutma süresini belirleyin.',
        'Denetlenmiş referans, teslim geçmişi ve kira varsayımlarını yazılı isteyin.',
        'Boşluk, işletme gideri ve faiz senaryolarıyla nakit akışını hesaplayıcılarla test edin.',
        'Ardından danışmanlık randevusu alın — model çıktılarınızı ve sorularınızı getirin.',
      ],
    },
    category: 'guides',
    tags: ['checklist', 'beginners', 'due-diligence'],
    author: { name: 'Investhome Insights', role: { en: 'Editorial', tr: 'Editoryal' } },
    publishedAt: '2026-05-12',
    readingMinutes: 6,
    relatedSlugs: ['rental-yield-basics', 'how-we-underwrite'],
    seo: {
      title: {
        en: 'First-time investor checklist | Investhome',
        tr: 'İlk yatırımcı kontrol listesi | Investhome',
      },
      description: {
        en: 'Step-by-step checklist for first-time real estate investors in Turkey.',
        tr: 'Türkiye’de ilk kez gayrimenkul yatırımı yapanlar için adım adım kontrol listesi.',
      },
    },
    workflow: {
      status: 'published',
      aiDraftAvailable: true,
      internalLinks: ['/calculators/rental-yield', '/lead/consultation', '/projects'],
    },
  },
  {
    slug: 'rental-yield-basics',
    title: {
      en: 'Rental yield basics: gross vs net',
      tr: 'Kira getirisi temelleri: brüt ve net',
    },
    excerpt: {
      en: 'How to read yield claims without overstating return.',
      tr: 'Getiri iddialarını abartmadan nasıl okursunuz.',
    },
    body: {
      en: [
        'Gross yield divides annual rent by purchase price — useful, incomplete.',
        'Net yield subtracts vacancy, management, tax, and maintenance.',
        'Always ask which costs are included when comparing projects.',
        'Use the rental yield calculator, then save results into a consultation request.',
      ],
      tr: [
        'Brüt getiri yıllık kirayı alış fiyatına böler — faydalı ama eksiktir.',
        'Net getiri boşluk, yönetim, vergi ve bakımı düşer.',
        'Projeleri karşılaştırırken hangi maliyetlerin dahil olduğunu sorun.',
        'Kira getirisi hesaplayıcısını kullanın, ardından sonuçları danışmanlık talebine kaydedin.',
      ],
    },
    category: 'investment',
    tags: ['yield', 'calculators', 'underwriting'],
    author: { name: 'Investhome Insights', role: { en: 'Editorial', tr: 'Editoryal' } },
    publishedAt: '2026-04-28',
    readingMinutes: 5,
    relatedSlugs: ['first-time-investor-checklist', 'cash-flow-discipline'],
    seo: {
      title: { en: 'Rental yield basics | Investhome', tr: 'Kira getirisi temelleri | Investhome' },
      description: {
        en: 'Understand gross vs net rental yield before you commit capital.',
        tr: 'Sermaye bağlamadan önce brüt ve net kira getirisini anlayın.',
      },
    },
    workflow: {
      status: 'published',
      aiDraftAvailable: true,
      internalLinks: ['/calculators/rental-yield', '/calculators/cash-flow'],
    },
  },
  {
    slug: 'cash-flow-discipline',
    title: {
      en: 'Cash flow discipline for leveraged buys',
      tr: 'Kaldıraçlı alımlarda nakit akışı disiplini',
    },
    excerpt: {
      en: 'Mortgage + opex scenarios that keep investments solvent through cycles.',
      tr: 'Döngüler boyunca yatırımı ayakta tutan mortgage ve işletme gideri senaryoları.',
    },
    body: {
      en: [
        'Model debt service coverage before chasing headline ROI.',
        'Include rate resets and refinance friction in multi-year plans.',
        'Pair the mortgage and cash-flow calculators, then request an investment analysis.',
      ],
      tr: [
        'Manşet ROI peşinde koşmadan önce borç servis karşılama oranını modelleyin.',
        'Çok yıllı planlara faiz yenilemesi ve refinansman sürtünmesini ekleyin.',
        'Mortgage ve nakit akışı hesaplayıcılarını birlikte kullanın, ardından yatırım analizi isteyin.',
      ],
    },
    category: 'investment',
    tags: ['cash-flow', 'mortgage', 'risk'],
    author: { name: 'Investhome Insights', role: { en: 'Editorial', tr: 'Editoryal' } },
    publishedAt: '2026-03-18',
    readingMinutes: 7,
    relatedSlugs: ['rental-yield-basics', '1031-exchange-overview'],
    seo: {
      title: { en: 'Cash flow discipline | Investhome', tr: 'Nakit akışı disiplini | Investhome' },
      description: {
        en: 'Keep leveraged real estate investments solvent with disciplined cash-flow modeling.',
        tr: 'Disiplinli nakit akışı modellemesiyle kaldıraçlı yatırımları ayakta tutun.',
      },
    },
    workflow: {
      status: 'published',
      aiDraftAvailable: true,
      internalLinks: ['/calculators/cash-flow', '/calculators/mortgage', '/lead/analysis'],
    },
  },
  {
    slug: 'istanbul-office-demand',
    title: {
      en: 'Istanbul office demand: what investors watch',
      tr: 'İstanbul ofis talebi: yatırımcılar neye bakıyor',
    },
    excerpt: {
      en: 'Signals from grade, transit access, and tenant mix — not just vacancy headlines.',
      tr: 'Sadece boşluk manşetleri değil; sınıf, ulaşım ve kiracı karması sinyalleri.',
    },
    body: {
      en: [
        'Grade and amenity packs increasingly separate absorbing assets from stale stock.',
        'Transit adjacency and parking economics still matter for hybrid schedules.',
        'Ask the investment team for current income-focused product examples.',
      ],
      tr: [
        'Sınıf ve olanak paketleri, emilen varlıkları durağan stoktan ayırıyor.',
        'Hibrit çalışma için ulaşım yakınlığı ve otopark ekonomisi hâlâ önemli.',
        'Güncel gelir odaklı ürün örnekleri için yatırım ekibiyle görüşün.',
      ],
    },
    category: 'market',
    tags: ['istanbul', 'office', 'demand'],
    author: { name: 'Investhome Insights', role: { en: 'Market desk', tr: 'Piyasa masası' } },
    publishedAt: '2026-02-09',
    readingMinutes: 8,
    relatedSlugs: ['how-we-underwrite', 'first-time-investor-checklist'],
    seo: {
      title: { en: 'Istanbul office demand | Investhome', tr: 'İstanbul ofis talebi | Investhome' },
      description: {
        en: 'What sophisticated investors monitor in Istanbul office markets.',
        tr: 'İstanbul ofis piyasasında deneyimli yatırımcıların izlediği sinyaller.',
      },
    },
    workflow: {
      status: 'published',
      aiDraftAvailable: true,
      internalLinks: ['/projects', '/insights'],
    },
  },
  {
    slug: 'how-we-underwrite',
    title: {
      en: 'How Investhome underwrites opportunities',
      tr: 'Investhome fırsatları nasıl değerlendirir',
    },
    excerpt: {
      en: 'A transparent look at assumptions, stress tests, and governance gates.',
      tr: 'Varsayımlar, stres testleri ve yönetişim kapılarına şeffaf bir bakış.',
    },
    body: {
      en: [
        'Every opportunity passes location, product, counterparty, and structure lenses.',
        'Stress cases are mandatory — base case alone is never enough.',
        'AI assists drafting memos; humans approve publish and investor communications.',
      ],
      tr: [
        'Her fırsat konum, ürün, karşı taraf ve yapı lenslerinden geçer.',
        'Stres senaryoları zorunludur — yalnızca baz senaryo yeterli değildir.',
        'AI memo taslaklarına yardımcı olur; yayın ve yatırımcı iletişimini insanlar onaylar.',
      ],
    },
    category: 'product',
    tags: ['process', 'governance', 'ai'],
    author: { name: 'Investhome Insights', role: { en: 'Product', tr: 'Ürün' } },
    publishedAt: '2026-01-22',
    readingMinutes: 6,
    relatedSlugs: ['cash-flow-discipline', '1031-exchange-overview'],
    seo: {
      title: { en: 'How we underwrite | Investhome', tr: 'Nasıl değerlendiriyoruz | Investhome' },
      description: {
        en: 'Governance and underwriting principles behind Investhome opportunities.',
        tr: 'Investhome fırsatlarının ardındaki yönetişim ve değerlendirme ilkeleri.',
      },
    },
    workflow: {
      status: 'published',
      aiDraftAvailable: true,
      internalLinks: ['/workflow', '/lead/consultation'],
    },
  },
  {
    slug: '1031-exchange-overview',
    title: {
      en: '1031 exchange overview (US investors)',
      tr: '1031 değişimi özeti (ABD yatırımcıları)',
    },
    excerpt: {
      en: 'Educational overview — not tax advice. Coordinate with qualified counsel.',
      tr: 'Eğitici özet — vergi tavsiyesi değildir. Yetkili danışmanla koordine edin.',
    },
    body: {
      en: [
        'A 1031 exchange can defer capital gains when like-kind rules are met.',
        'Timelines and identification rules are strict; planning starts before sale.',
        'Use our 1031 calculator for scenario framing, then schedule a meeting with advisors.',
      ],
      tr: [
        '1031 değişimi, benzer tür kuralları sağlandığında sermaye kazancını erteleyebilir.',
        'Süreler ve tanımlama kuralları katıdır; planlama satıştan önce başlar.',
        'Senaryo çerçevesi için 1031 hesaplayıcımızı kullanın, ardından danışmanlarla toplantı planlayın.',
      ],
    },
    category: 'tax',
    tags: ['1031', 'us', 'structure'],
    author: { name: 'Investhome Insights', role: { en: 'Editorial', tr: 'Editoryal' } },
    publishedAt: '2025-12-10',
    readingMinutes: 9,
    relatedSlugs: ['cash-flow-discipline', 'how-we-underwrite'],
    seo: {
      title: { en: '1031 exchange overview | Investhome', tr: '1031 değişimi özeti | Investhome' },
      description: {
        en: 'Educational overview of 1031 exchanges for US real estate investors.',
        tr: 'ABD gayrimenkul yatırımcıları için 1031 değişimine eğitici bakış.',
      },
    },
    workflow: {
      status: 'published',
      aiDraftAvailable: true,
      internalLinks: ['/calculators/1031', '/lead/meeting'],
    },
  },
];

export function getLatestArticles(limit = 3): SiteArticle[] {
  return [...SITE_ARTICLES]
    .filter((a) => a.workflow.status === 'published')
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt))
    .slice(0, limit);
}

export function getArticleBySlug(slug: string): SiteArticle | undefined {
  return SITE_ARTICLES.find((a) => a.slug === slug);
}

export function getArticlesByCategory(category?: SiteArticleCategory): SiteArticle[] {
  const published = SITE_ARTICLES.filter((a) => a.workflow.status === 'published');
  if (!category) return published.sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
  return published
    .filter((a) => a.category === category)
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
}

export function searchArticles(query: string): SiteArticle[] {
  const q = query.trim().toLowerCase();
  if (!q) return getArticlesByCategory();
  return getArticlesByCategory().filter((a) => {
    const hay = [
      a.slug,
      a.title.en,
      a.title.tr,
      a.excerpt.en,
      a.excerpt.tr,
      ...a.tags,
      a.category,
    ]
      .join(' ')
      .toLowerCase();
    return hay.includes(q);
  });
}

export function getRelatedArticles(slug: string, limit = 3): SiteArticle[] {
  const article = getArticleBySlug(slug);
  if (!article) return [];
  const related = article.relatedSlugs
    .map((s) => getArticleBySlug(s))
    .filter((a): a is SiteArticle => Boolean(a));
  if (related.length >= limit) return related.slice(0, limit);
  const fillers = getLatestArticles(6).filter(
    (a) => a.slug !== slug && !related.some((r) => r.slug === a.slug),
  );
  return [...related, ...fillers].slice(0, limit);
}

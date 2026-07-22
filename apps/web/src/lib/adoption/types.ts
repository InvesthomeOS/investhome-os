/** G13 Adoption / Training — shared types */

export type LocaleText = { en: string; tr: string };

export type AdoptionRoleId =
  | 'ceo'
  | 'cfo'
  | 'sales_manager'
  | 'sales_rep'
  | 'investor_relations'
  | 'project_manager'
  | 'construction_ops'
  | 'finance'
  | 'marketing'
  | 'operations'
  | 'admin'
  | 'executive_assistant'
  | 'portal_investor';

export type PathStatus =
  | 'not_started'
  | 'in_progress'
  | 'completed'
  | 'overdue'
  | 'exempted'
  | 'needs_review';

export type ContentStatus = 'draft' | 'review' | 'published' | 'outdated' | 'archived';

export type TourType =
  | 'informational'
  | 'guided_click'
  | 'guided_form'
  | 'guided_workflow'
  | 'mandatory_compliance'
  | 'new_feature';

export type TourStep = {
  id: string;
  title: LocaleText;
  description: LocaleText;
  action: LocaleText;
  expectedResult: LocaleText;
  selector: string;
  helpLink?: string;
  warning?: LocaleText;
  completionCondition: 'viewed' | 'clicked' | 'form_filled' | 'route_visited';
  placement?: 'top' | 'bottom' | 'left' | 'right';
};

export type ProductTour = {
  id: string;
  title: LocaleText;
  description: LocaleText;
  type: TourType;
  roles: AdoptionRoleId[];
  route: string;
  estimatedMinutes: number;
  skipAllowed: boolean;
  steps: TourStep[];
  version: string;
  status: ContentStatus;
  adminOnly?: boolean;
};

export type LearningModule = {
  id: string;
  title: LocaleText;
  mandatory: boolean;
  estimatedMinutes: number;
  tourId?: string;
  tutorialId?: string;
  checklistId?: string;
  knowledgeCheckId?: string;
};

export type LearningPath = {
  id: string;
  roleId: AdoptionRoleId;
  title: LocaleText;
  description: LocaleText;
  modules: LearningModule[];
  practicalTasks: LocaleText[];
  teachTopics: LocaleText[];
  deadlineDays: number;
  version: string;
  status: ContentStatus;
};

export type ChecklistCadence = 'daily' | 'weekly' | 'monthly';

export type ChecklistItem = {
  id: string;
  title: LocaleText;
  description: LocaleText;
  ownerRole: AdoptionRoleId;
  relatedWorkspace: string;
  completionCriteria: LocaleText;
  escalationRule: LocaleText;
};

export type OperationalChecklist = {
  id: string;
  cadence: ChecklistCadence;
  roleId: AdoptionRoleId;
  title: LocaleText;
  items: ChecklistItem[];
  version: string;
  status: ContentStatus;
};

export type WorkflowTutorial = {
  id: string;
  title: LocaleText;
  purpose: LocaleText;
  responsibleRole: AdoptionRoleId;
  prerequisites: LocaleText[];
  steps: LocaleText[];
  expectedResult: LocaleText;
  commonMistakes: LocaleText[];
  approvalRequirements: LocaleText;
  relatedHelpIds: string[];
  version: string;
  status: ContentStatus;
};

export type HelpArticle = {
  id: string;
  title: LocaleText;
  summary: LocaleText;
  body: LocaleText;
  category: string;
  contentType:
    | 'article'
    | 'faq'
    | 'policy'
    | 'release_note'
    | 'troubleshooting'
    | 'role_guide'
    | 'quick_reference';
  roles: AdoptionRoleId[] | ['*'];
  workspaces: string[];
  relatedRoutes: string[];
  adminOnly?: boolean;
  version: string;
  status: ContentStatus;
  lastUpdated: string;
  owner: string;
  durationMinutes?: number;
  difficulty?: 'beginner' | 'intermediate' | 'advanced';
};

export type Playbook = {
  id: string;
  title: LocaleText;
  trigger: LocaleText;
  responsibleRole: AdoptionRoleId;
  steps: LocaleText[];
  slaId: string;
  escalationPath: LocaleText;
  requiredEvidence: LocaleText[];
  completionCriteria: LocaleText;
  auditRequirements: LocaleText;
  version: string;
  status: ContentStatus;
};

export type SlaDefinition = {
  id: string;
  title: LocaleText;
  event: LocaleText;
  ownerRole: AdoptionRoleId;
  responseTargetMinutes: number;
  resolutionTargetHours: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  escalationThresholdMinutes: number;
  escalationRecipient: LocaleText;
  notificationBehavior: LocaleText;
  businessHours: boolean;
  timezone: string;
  linkedAutomation?: string;
};

export type KnowledgeCheckQuestion = {
  id: string;
  type: 'multiple_choice' | 'true_false' | 'scenario' | 'ordering' | 'identify_action';
  prompt: LocaleText;
  options: LocaleText[];
  correctIndex: number;
  explanation: LocaleText;
};

export type KnowledgeCheck = {
  id: string;
  title: LocaleText;
  roleId: AdoptionRoleId;
  questions: KnowledgeCheckQuestion[];
  passScore: number;
  version: string;
  status: ContentStatus;
};

export type Certification = {
  id: string;
  title: LocaleText;
  roleIds: AdoptionRoleId[];
  requiredModuleIds: string[];
  requiredSimulationId?: string;
  requiredKnowledgeCheckId?: string;
  managerApprovalRequired: boolean;
  renewalMonths: number | null;
  version: string;
  status: ContentStatus;
};

export type SimulationScenario = {
  id: string;
  title: LocaleText;
  description: LocaleText;
  roleId: AdoptionRoleId;
  steps: LocaleText[];
  labels: string[];
  blocksRealActions: true;
};

export type ContextualGuidance = {
  id: string;
  routePattern: string;
  title: LocaleText;
  tips: LocaleText[];
  pattern: 'tooltip' | 'info_panel' | 'inline_warning' | 'empty_state' | 'side_panel';
};

export type CapabilityAuditStatus = 'LIVE' | 'PARTIAL' | 'DEMO' | 'BLOCKED' | 'NOT CONFIGURED';

export type CapabilityAuditItem = {
  id: string;
  name: string;
  status: CapabilityAuditStatus;
  notes: string;
};

export type FeedbackType =
  | 'helpful'
  | 'not_helpful'
  | 'confusing'
  | 'missing_information'
  | 'broken_tour'
  | 'outdated_content'
  | 'feature_request'
  | 'bug_report';

export type SupportCategory =
  | 'access'
  | 'data'
  | 'crm'
  | 'investor'
  | 'project'
  | 'finance'
  | 'marketing'
  | 'ai'
  | 'document'
  | 'portal'
  | 'bug'
  | 'training'
  | 'security'
  | 'other';

export type BuilderDraft = {
  id: string;
  title: string;
  description: string;
  contentType: string;
  workspace: string;
  route: string;
  role: AdoptionRoleId | '';
  language: 'tr' | 'en';
  version: string;
  owner: string;
  status: ContentStatus;
  targetSelector: string;
  completionCondition: string;
  prerequisite: string;
  deadline: string;
  mandatory: boolean;
  estimatedDuration: number;
};

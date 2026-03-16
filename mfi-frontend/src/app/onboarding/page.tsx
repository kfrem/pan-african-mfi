'use client';
import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Building2, Palette, Globe, BookOpen, Package, GitBranch,
  Users, UserPlus, FileText, Shield, MessageSquare, Upload,
  Check, ChevronRight, ArrowRight, Sparkles
} from 'lucide-react';
import type { OnboardingStep } from '@/types';
import { apiService } from '@/lib/api-service';

const STEPS: { step: string; label: string; description: string; icon: React.ElementType }[] = [
  { step: 'institution_profile', label: 'Set up your institution', description: 'Name, address, and contact details', icon: Building2 },
  { step: 'upload_logo', label: 'Brand your dashboard', description: 'Upload logo and choose colours', icon: Palette },
  { step: 'country_and_tier', label: 'Select country & licence', description: 'Regulatory configuration auto-loads', icon: Globe },
  { step: 'chart_of_accounts', label: 'Chart of accounts', description: 'Use our template or customise', icon: BookOpen },
  { step: 'loan_products', label: 'Set up loan products', description: 'Define your lending products', icon: Package },
  { step: 'branches', label: 'Create branches', description: 'Add your physical or logical branches', icon: GitBranch },
  { step: 'users_and_roles', label: 'Invite your team', description: 'Add staff and assign roles', icon: Users },
  { step: 'first_client', label: 'Register first client', description: 'Test the client onboarding flow', icon: UserPlus },
  { step: 'first_loan', label: 'Create first loan', description: 'Test the loan application workflow', icon: FileText },
  { step: 'maker_checker', label: 'Configure approvals', description: 'Set up maker-checker workflows', icon: Shield },
  { step: 'sms_setup', label: 'SMS reminders', description: 'Configure automated SMS (optional)', icon: MessageSquare },
  { step: 'import_data', label: 'Import existing data', description: 'Upload clients and loans from CSV (optional)', icon: Upload },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [skippedSteps, setSkippedSteps] = useState<Set<string>>(new Set());
  const [loadDemo, setLoadDemo] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importStatus, setImportStatus] = useState<'idle' | 'validating' | 'validated' | 'importing' | 'done' | 'error'>('idle');
  const [importJobId, setImportJobId] = useState<string | null>(null);
  const [importMessage, setImportMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImportFile = async (file: File) => {
    setImportFile(file);
    setImportStatus('validating');
    setImportMessage('Validating file...');
    const job = await apiService.validateImport('clients', file);
    if (!job) {
      setImportStatus('error');
      setImportMessage('Validation failed. Please check your file format.');
      return;
    }
    setImportJobId(job.id);
    setImportStatus('validated');
    setImportMessage(`${job.valid_rows ?? 0} valid rows, ${job.error_rows ?? 0} errors. Click Import to proceed.`);
  };

  const handleCommitImport = async () => {
    if (!importJobId) return;
    setImportStatus('importing');
    setImportMessage('Importing...');
    await apiService.commitImport(importJobId);
    setImportStatus('done');
    setImportMessage('Import complete!');
  };

  const current = STEPS[currentStep];
  const progress = (completedSteps.size / STEPS.length) * 100;

  const completeStep = () => {
    setCompletedSteps(prev => new Set([...prev, current.step]));
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      router.push('/dashboard');
    }
  };

  const skipStep = () => {
    setSkippedSteps(prev => new Set([...prev, current.step]));
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: '#060a14' }} data-theme="bloomberg">
      {/* Header */}
      <div className="border-b" style={{ borderColor: '#1a2744', background: '#0c1222' }}>
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm"
                 style={{ background: 'linear-gradient(135deg, #0066ff, #8b5cf6)' }}>
              M
            </div>
            <div>
              <div className="text-sm font-semibold text-white">Platform Setup</div>
              <div className="text-xs text-gray-500">Step {currentStep + 1} of {STEPS.length}</div>
            </div>
          </div>

          {/* Progress bar */}
          <div className="flex items-center gap-3">
            <div className="w-48 h-1.5 rounded-full" style={{ background: '#1a2744' }}>
              <div className="h-full rounded-full transition-all duration-500"
                   style={{ width: `${progress}%`, background: 'linear-gradient(90deg, #0066ff, #8b5cf6)' }} />
            </div>
            <span className="text-xs text-gray-500 font-semibold">{Math.round(progress)}%</span>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8 flex gap-8">
        {/* Step sidebar */}
        <div className="w-72 shrink-0">
          <div className="space-y-1">
            {STEPS.map((step, idx) => {
              const isCompleted = completedSteps.has(step.step);
              const isSkipped = skippedSteps.has(step.step);
              const isCurrent = idx === currentStep;
              const Icon = step.icon;

              return (
                <button key={step.step}
                        onClick={() => setCurrentStep(idx)}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                          isCurrent ? 'border' : ''
                        }`}
                        style={{
                          background: isCurrent ? 'rgba(0,102,255,0.1)' : 'transparent',
                          borderColor: isCurrent ? 'rgba(0,102,255,0.3)' : 'transparent',
                        }}>
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold ${
                    isCompleted ? 'bg-status-current text-white' :
                    isSkipped ? 'text-gray-600' :
                    isCurrent ? 'text-white' : 'text-gray-600'
                  }`} style={{
                    background: isCompleted ? '' : isCurrent ? 'var(--brand-primary)' : '#1a2744'
                  }}>
                    {isCompleted ? <Check className="w-3.5 h-3.5" /> : <Icon className="w-3.5 h-3.5" />}
                  </div>
                  <div className="min-w-0">
                    <div className={`text-xs font-semibold truncate ${
                      isCurrent ? 'text-white' : isCompleted ? 'text-status-current' : 'text-gray-400'
                    }`}>{step.label}</div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Demo data toggle */}
          <div className="mt-8 p-4 rounded-lg" style={{ background: '#0c1222', border: '1px solid #1a2744' }}>
            <label className="flex items-start gap-3 cursor-pointer">
              <input type="checkbox" checked={loadDemo} onChange={(e) => setLoadDemo(e.target.checked)}
                     className="mt-1 rounded" />
              <div>
                <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-yellow-400" />
                  Load demo data
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  Pre-fill with 10 sample clients, 5 loans, and example reports so you can explore immediately.
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Main content area */}
        <div className="flex-1">
          <div className="rounded-xl p-8" style={{ background: '#0c1222', border: '1px solid #1a2744' }}>
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center"
                   style={{ background: 'rgba(0,102,255,0.15)' }}>
                <current.icon className="w-6 h-6" style={{ color: '#0066ff' }} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">{current.label}</h2>
                <p className="text-sm text-gray-400">{current.description}</p>
              </div>
            </div>

            {/* Step content */}
            {current.step === 'import_data' ? (
              <div className="min-h-[300px] flex flex-col items-center justify-center rounded-lg p-8 gap-4"
                   style={{ background: '#060a14', border: '1px dashed #1a2744' }}>
                <Upload className="w-10 h-10 text-gray-500" />
                <p className="text-sm text-gray-400">Upload a CSV of your existing clients and loans</p>
                <input ref={fileInputRef} type="file" accept=".csv,.xlsx" className="hidden"
                       onChange={e => { if (e.target.files?.[0]) handleImportFile(e.target.files[0]); }} />
                <button onClick={() => fileInputRef.current?.click()}
                        className="px-4 py-2 rounded-lg text-sm font-semibold"
                        style={{ background: 'rgba(0,102,255,0.15)', color: '#0066ff', border: '1px solid rgba(0,102,255,0.3)' }}>
                  {importFile ? importFile.name : 'Choose File'}
                </button>
                {importMessage && <p className={`text-xs ${importStatus === 'error' ? 'text-red-400' : 'text-gray-400'}`}>{importMessage}</p>}
                {importStatus === 'validated' && (
                  <button onClick={handleCommitImport}
                          className="px-4 py-2 rounded-lg text-sm font-semibold"
                          style={{ background: '#0066ff', color: '#fff' }}>
                    Import Data
                  </button>
                )}
              </div>
            ) : (
              <div className="min-h-[300px] flex items-center justify-center rounded-lg p-8"
                   style={{ background: '#060a14', border: '1px dashed #1a2744' }}>
                <div className="text-center">
                  <current.icon className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                  <p className="text-sm text-gray-500">
                    {current.step === 'institution_profile' && 'Enter your institution name, registration number, and address'}
                    {current.step === 'upload_logo' && 'Upload your logo (SVG or PNG) and pick your brand colours'}
                    {current.step === 'country_and_tier' && 'Select Ghana or Zambia — regulatory rules load automatically'}
                    {current.step === 'chart_of_accounts' && 'We\'ll create a standard chart of accounts for your country — you can customise it later'}
                    {current.step === 'loan_products' && 'Define your micro-loan, group loan, SME, and emergency loan products'}
                    {current.step === 'branches' && 'Add your branches — they\'ll be used for portfolio reporting and staff assignment'}
                    {current.step === 'users_and_roles' && 'Invite loan officers, managers, and other staff by email'}
                    {current.step === 'first_client' && 'Walk through the client registration form with KYC fields'}
                    {current.step === 'first_loan' && 'Create a test loan application to see the full workflow'}
                    {current.step === 'maker_checker' && 'Choose how many approvals are needed for loans, write-offs, and rate changes'}
                    {current.step === 'sms_setup' && 'Connect Africa\'s Talking for automated repayment SMS reminders'}
                  </p>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-between mt-6">
              {current.step.includes('sms') || current.step.includes('import') ? (
                <button onClick={skipStep} className="btn-secondary text-sm">
                  Skip for now
                </button>
              ) : (
                <div />
              )}
              <button onClick={completeStep} className="btn-primary">
                {currentStep === STEPS.length - 1 ? (
                  <>Launch Dashboard <ArrowRight className="w-4 h-4" /></>
                ) : (
                  <>Complete & Continue <ChevronRight className="w-4 h-4" /></>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

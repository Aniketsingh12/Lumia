import { useState, useEffect } from 'react'
import { Save, Plus, X, Sparkles, FileText, Loader2 } from 'lucide-react'
import { useBotStore, type Bot } from '../../stores/botStore'
import { BOT_GENRES, getGenre } from '../../lib/genres'
import { getPromptSample } from '../../lib/promptSamples'
import api, { getErrorMessage } from '../../lib/api'
import { cn } from '../../lib/utils'
import toast from 'react-hot-toast'

const toneOptions = ['professional', 'friendly', 'casual', 'witty', 'custom']

interface PersonalityTabProps {
  bot: Bot
}

export default function PersonalityTab({ bot }: PersonalityTabProps) {
  const { updateBot } = useBotStore()
  const [name, setName] = useState(bot.name)
  const [botType, setBotType] = useState(bot.bot_type || 'support')
  const [persona, setPersona] = useState(bot.persona || '')
  const [tone, setTone] = useState(bot.tone)
  const [greeting, setGreeting] = useState(bot.greeting_message)
  const [fallback, setFallback] = useState(bot.fallback_message)
  const [rules, setRules] = useState<string[]>(bot.custom_rules || [])
  const [newRule, setNewRule] = useState('')
  const [saving, setSaving] = useState(false)

  // Custom system prompt (advanced) + AI generator
  const [customPrompt, setCustomPrompt] = useState(bot.system_prompt_override || '')
  const [showPromptTools, setShowPromptTools] = useState(false)
  const [genDescription, setGenDescription] = useState('')
  const [generating, setGenerating] = useState(false)

  const selectedGenre = getGenre(botType)

  useEffect(() => {
    setName(bot.name)
    setBotType(bot.bot_type || 'support')
    setPersona(bot.persona || '')
    setTone(bot.tone)
    setGreeting(bot.greeting_message)
    setFallback(bot.fallback_message)
    setRules(bot.custom_rules || [])
    setCustomPrompt(bot.system_prompt_override || '')
    setShowPromptTools(!!bot.system_prompt_override)
  }, [bot])

  const insertSample = () => {
    setCustomPrompt(getPromptSample(botType))
    toast.success('Sample inserted — edit it to fit your bot')
  }

  const generatePrompt = async () => {
    if (!genDescription.trim()) {
      toast.error('Describe what your bot should do first')
      return
    }
    setGenerating(true)
    try {
      const { data } = await api.post('/bots/generate-prompt', {
        description: genDescription,
        bot_type: botType,
        name,
        tone,
      })
      setCustomPrompt(data.prompt)
      toast.success('Prompt generated!')
    } catch (err) {
      toast.error(getErrorMessage(err, 'Could not generate a prompt'))
    }
    setGenerating(false)
  }

  const addRule = () => {
    if (newRule.trim()) {
      setRules([...rules, newRule.trim()])
      setNewRule('')
    }
  }

  const removeRule = (index: number) => {
    setRules(rules.filter((_, i) => i !== index))
  }

  const handleSave = async () => {
    if (selectedGenre.usesPersona && !persona.trim()) {
      toast.error('Character bots need a persona description')
      return
    }
    setSaving(true)
    try {
      await updateBot(bot.id, {
        name,
        bot_type: botType,
        // Empty string (not null) so the backend's exclude_none update can clear it
        persona: persona.trim(),
        tone,
        greeting_message: greeting,
        fallback_message: fallback,
        custom_rules: rules,
        // Empty string clears the override and reverts to the genre preset
        system_prompt_override: customPrompt.trim(),
      })
      toast.success('Bot updated!')
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update'))
    }
    setSaving(false)
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Name */}
      <div>
        <label className="label">Bot Name</label>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input" />
      </div>

      {/* Genre */}
      <div>
        <label className="label">Bot Type</label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {BOT_GENRES.map((genre) => (
            <button
              key={genre.id}
              type="button"
              onClick={() => setBotType(genre.id)}
              className={cn(
                'text-left p-3 rounded-lg border transition-colors',
                botType === genre.id
                  ? 'bg-primary-50 border-primary-300'
                  : 'bg-white border-gray-200 hover:border-gray-300'
              )}
            >
              <div className="flex items-center gap-2">
                <genre.icon
                  className={cn(
                    'w-4 h-4 flex-shrink-0',
                    botType === genre.id ? 'text-primary-600' : 'text-gray-400'
                  )}
                />
                <span
                  className={cn(
                    'text-sm font-medium',
                    botType === genre.id ? 'text-primary-700' : 'text-gray-700'
                  )}
                >
                  {genre.label}
                </span>
              </div>
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-1">{selectedGenre.description}</p>
      </div>

      {/* Persona — the whole identity for character bots, optional color for others */}
      <div>
        <label className="label">
          {selectedGenre.usesPersona ? 'Character Persona' : 'Persona (optional)'}
        </label>
        <textarea
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          className="input min-h-[80px] resize-y"
          rows={3}
          placeholder={
            selectedGenre.personaPlaceholder ||
            'e.g., A 10-year veteran of the company who knows every product detail'
          }
        />
        <p className="text-xs text-gray-400 mt-1">
          {selectedGenre.usesPersona
            ? 'The bot fully becomes this character in every chat'
            : 'Extra character details woven into the bot’s identity'}
        </p>
      </div>

      {/* Tone */}
      <div>
        <label className="label">Tone</label>
        <div className="flex flex-wrap gap-2">
          {toneOptions.map((t) => (
            <button
              key={t}
              onClick={() => setTone(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors capitalize ${
                tone === t
                  ? 'bg-primary-50 border-primary-300 text-primary-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Greeting */}
      <div>
        <label className="label">Greeting Message</label>
        <textarea
          value={greeting}
          onChange={(e) => setGreeting(e.target.value)}
          className="input min-h-[80px] resize-y"
          rows={3}
        />
        <p className="text-xs text-gray-400 mt-1">First message visitors see when they open the chat</p>
      </div>

      {/* Fallback */}
      <div>
        <label className="label">Fallback Message</label>
        <textarea
          value={fallback}
          onChange={(e) => setFallback(e.target.value)}
          className="input min-h-[80px] resize-y"
          rows={3}
        />
        <p className="text-xs text-gray-400 mt-1">Sent when the bot can't answer confidently</p>
      </div>

      {/* Rules */}
      <div>
        <label className="label">Custom Rules</label>
        <div className="space-y-2 mb-3">
          {rules.map((rule, i) => (
            <div key={i} className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
              <span className="flex-1 text-sm text-gray-700">{rule}</span>
              <button onClick={() => removeRule(i)} className="text-gray-400 hover:text-red-500">
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newRule}
            onChange={(e) => setNewRule(e.target.value)}
            className="input flex-1"
            placeholder="e.g., Never mention competitor names"
            onKeyDown={(e) => e.key === 'Enter' && addRule()}
          />
          <button onClick={addRule} className="btn-secondary">
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Advanced: Custom System Prompt */}
      <div className="border-t border-gray-200 pt-6">
        <div className="flex items-center justify-between">
          <div>
            <label className="label mb-0">Custom System Prompt</label>
            <p className="text-xs text-gray-400 mt-0.5">
              Advanced — write the bot's whole prompt yourself. Overrides the{' '}
              <span className="font-medium">{selectedGenre.label}</span> preset above.
            </p>
          </div>
          {!showPromptTools && (
            <button
              type="button"
              onClick={() => setShowPromptTools(true)}
              className="btn-secondary text-sm"
            >
              Customize
            </button>
          )}
        </div>

        {showPromptTools && (
          <div className="mt-3 space-y-3">
            {/* Generator + sample buttons */}
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
              <p className="text-xs font-medium text-gray-600 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-primary-500" />
                Not sure what to write? Describe your bot and let AI draft it:
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={genDescription}
                  onChange={(e) => setGenDescription(e.target.value)}
                  className="input flex-1 text-sm"
                  placeholder="e.g., A support bot for my bakery that helps with orders and allergies"
                  onKeyDown={(e) => e.key === 'Enter' && !generating && generatePrompt()}
                />
                <button
                  type="button"
                  onClick={generatePrompt}
                  disabled={generating}
                  className="btn-primary text-sm flex items-center gap-1.5 whitespace-nowrap"
                >
                  {generating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  {generating ? 'Writing…' : 'Generate'}
                </button>
              </div>
              <button
                type="button"
                onClick={insertSample}
                className="text-xs text-primary-600 font-medium hover:text-primary-700 flex items-center gap-1"
              >
                <FileText className="w-3.5 h-3.5" />
                Or insert a {selectedGenre.label} sample to edit
              </button>
            </div>

            {/* The prompt itself */}
            <textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              className="input min-h-[160px] resize-y font-mono text-sm leading-relaxed"
              rows={7}
              placeholder="You are… (leave empty to use the genre preset). Your knowledge base and chat history are added automatically."
            />
            <div className="flex items-center justify-between">
              <p className="text-xs text-gray-400">
                Knowledge base + conversation history are injected automatically — don't add them here.
              </p>
              {customPrompt.trim() && (
                <button
                  type="button"
                  onClick={() => setCustomPrompt('')}
                  className="text-xs text-gray-400 hover:text-red-500"
                >
                  Clear &amp; use preset
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Save */}
      <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
        <Save className="w-4 h-4" />
        {saving ? 'Saving...' : 'Save Changes'}
      </button>
    </div>
  )
}

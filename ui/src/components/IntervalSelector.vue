<template>
  <div>
    <v-btn-toggle
      :model-value="selected"
      :density
      mandatory
      shaped
      divided
      variant="outlined"
      base-color="#898B8E"
      height="40"
      block
      @update:model-value="handleToggle"
    >
      <v-btn class="text-subtitle-2 text-medium-emphasis" color="primary" value="86400">
        Daily
      </v-btn>
      <v-btn class="text-subtitle-2 text-medium-emphasis" color="primary" value="604800">
        Weekly
      </v-btn>
      <v-btn class="text-subtitle-2 text-medium-emphasis" color="primary" value="2629746">
        Monthly
      </v-btn>
      <v-btn
        class="text-subtitle-2 text-medium-emphasis"
        color="primary"
        value="custom"
        data-test="selector-custom"
      >
        Custom interval
      </v-btn>
    </v-btn-toggle>
    <div v-if="selected == 'custom'" class="pt-3 reduced-input">
      <v-text-field
        v-model="custom"
        :density
        data-test="input"
        label="Every"
        variant="outlined"
        hide-details
        @update:model-value="handleInput"
      >
        <template #append-inner>
          <span class="text-medium-emphasis">seconds</span>
        </template>
      </v-text-field>
    </div>
  </div>
</template>
<script>
export default {
  name: 'IntervalSelector',
  emits: ['update:model-value'],
  props: {
    modelValue: {
      type: [String, Number],
      required: false,
      default: ''
    },
    density: {
      type: String,
      required: false,
      default: 'compact'
    }
  },
  data() {
    return {
      selected: this.modelValue,
      custom: ''
    }
  },
  methods: {
    handleToggle(event) {
      const value = event === 'custom' ? this.custom : event
      this.selected = event
      this.$emit('update:model-value', value)
    },
    handleInput(event) {
      if (this.selected === 'custom') {
        this.$emit('update:model-value', event)
      }
    }
  },
  mounted() {
    const setValues = [86400, 604800, 2629746]
    if (setValues.find((value) => value == this.modelValue)) {
      this.selected = this.modelValue
    } else {
      this.selected = 'custom'
      this.custom = this.modelValue
    }
  }
}
</script>
<style lang="scss" scoped>
.reduced-input {
  max-width: 366px;
}
</style>
